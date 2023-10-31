"""
This addon determines the next protocol layer in our proxy stack.
Whenever a protocol layer in the proxy wants to pass a connection to a child layer and isn't sure which protocol comes
next, it calls the `next_layer` hook, which ends up here.
For example, if mitmproxy runs as a regular proxy, we first need to determine if
new clients start with a TLS handshake right away (Secure Web Proxy) or send a plaintext HTTP CONNECT request.
This addon here peeks at the incoming bytes and then makes a decision based on proxy mode, mitmproxy options, etc.

For a typical HTTPS request, this addon is called a couple of times: First to determine that we start with an HTTP layer
which processes the `CONNECT` request, a second time to determine that the client then starts negotiating TLS, and a
third time when we check if the protocol within that TLS stream is actually HTTP or something else.

Sometimes it's useful to hardcode specific logic in next_layer when one wants to do fancy things.
In that case it's not necessary to modify mitmproxy's source, adding a custom addon with a next_layer event hook
that sets nextlayer.layer works just as well.
"""
from __future__ import annotations

import logging
import re
import struct
import sys
from collections.abc import Iterable
from collections.abc import Sequence
from typing import Any
from typing import cast

from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy import exceptions
from mitmproxy.net.tls import starts_like_dtls_record
from mitmproxy.net.tls import starts_like_tls_record
from mitmproxy.proxy import layer
from mitmproxy.proxy import layers
from mitmproxy.proxy import mode_specs
from mitmproxy.proxy import tunnel
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layer import Layer
from mitmproxy.proxy.layers import ClientQuicLayer
from mitmproxy.proxy.layers import ClientTLSLayer
from mitmproxy.proxy.layers import DNSLayer
from mitmproxy.proxy.layers import HttpLayer
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers import RawQuicLayer
from mitmproxy.proxy.layers import ServerQuicLayer
from mitmproxy.proxy.layers import ServerTLSLayer
from mitmproxy.proxy.layers import TCPLayer
from mitmproxy.proxy.layers import UDPLayer
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.layers.quic import quic_parse_client_hello
from mitmproxy.proxy.layers.tls import dtls_parse_client_hello
from mitmproxy.proxy.layers.tls import HTTP_ALPNS
from mitmproxy.proxy.layers.tls import parse_client_hello
from mitmproxy.tls import ClientHello

if sys.version_info < (3, 11):
    from typing_extensions import assert_never
else:
    from typing import assert_never

logger = logging.getLogger(__name__)


def stack_match(
    context: Context, layers: Sequence[type[Layer] | tuple[type[Layer], ...]]
) -> bool:
    if len(context.layers) != len(layers):
        return False
    return all(
        expected is Any or isinstance(actual, expected)
        for actual, expected in zip(context.layers, layers)
    )


class NeedsMoreData(Exception):
    """Signal that the decision on which layer to put next needs to be deferred within the NextLayer addon."""


class NextLayer:
    ignore_hosts: Sequence[re.Pattern] = ()
    allow_hosts: Sequence[re.Pattern] = ()
    tcp_hosts: Sequence[re.Pattern] = ()
    udp_hosts: Sequence[re.Pattern] = ()

    def configure(self, updated):
        if "tcp_hosts" in updated:
            self.tcp_hosts = [
                re.compile(x, re.IGNORECASE) for x in ctx.options.tcp_hosts
            ]
        if "udp_hosts" in updated:
            self.udp_hosts = [
                re.compile(x, re.IGNORECASE) for x in ctx.options.udp_hosts
            ]
        if "allow_hosts" in updated or "ignore_hosts" in updated:
            if ctx.options.allow_hosts and ctx.options.ignore_hosts:
                raise exceptions.OptionsError(
                    "The allow_hosts and ignore_hosts options are mutually exclusive."
                )
            self.ignore_hosts = [
                re.compile(x, re.IGNORECASE) for x in ctx.options.ignore_hosts
            ]
            self.allow_hosts = [
                re.compile(x, re.IGNORECASE) for x in ctx.options.allow_hosts
            ]

    def next_layer(self, nextlayer: layer.NextLayer):
        if nextlayer.layer:
            return  # do not override something another addon has set.
        try:
            nextlayer.layer = self._next_layer(
                nextlayer.context,
                nextlayer.data_client(),
                nextlayer.data_server(),
            )
        except NeedsMoreData:
            logger.info(
                f"Deferring layer decision, not enough data: {nextlayer.data_client().hex()}"
            )

    def _next_layer(
        self, context: Context, data_client: bytes, data_server: bytes
    ) -> Layer | None:
        assert context.layers

        def s(*layers):
            return stack_match(context, layers)

        tcp_based = context.client.transport_protocol == "tcp"
        udp_based = context.client.transport_protocol == "udp"

        # 1)  check for --ignore/--allow
        if self._ignore_connection(context, data_client):
            return (
                layers.TCPLayer(context, ignore=True)
                if tcp_based
                else layers.UDPLayer(context, ignore=True)
            )

        # 2)  Handle proxy modes with well-defined next protocol
        # 2a) Reverse proxy: derive from spec
        if s(modes.ReverseProxy):
            return self._setup_reverse_proxy(context, data_client)
        # 2b) Explicit HTTP proxies
        if s((modes.HttpProxy, modes.HttpUpstreamProxy)):
            return self._setup_explicit_http_proxy(context, data_client)

        # 3)  Handle security protocols
        # 3a) TLS/DTLS
        is_tls_or_dtls = (
            tcp_based
            and starts_like_tls_record(data_client)
            or udp_based
            and starts_like_dtls_record(data_client)
        )
        if is_tls_or_dtls:
            server_tls = ServerTLSLayer(context)
            server_tls.child_layer = ClientTLSLayer(context)
            return server_tls
        # 3b) QUIC
        if udp_based and _starts_like_quic(data_client):
            server_quic = ServerQuicLayer(context)
            server_quic.child_layer = ClientQuicLayer(context)
            return server_quic

        # 4)  Check for --tcp/--udp
        if tcp_based and self._is_destination_in_hosts(context, self.tcp_hosts):
            return layers.TCPLayer(context)
        if udp_based and self._is_destination_in_hosts(context, self.udp_hosts):
            return layers.UDPLayer(context)

        # 5)  Handle application protocol
        # 5a) Is it DNS?
        if udp_based:
            try:
                # TODO: DNS over TCP
                dns.Message.unpack(data_client)  # TODO: perf
            except struct.error:
                pass
            else:
                return layers.DNSLayer(context)
        # 5b) We have no other specialized layers for UDP, so we fall back to raw forwarding.
        if udp_based:
            return layers.UDPLayer(context)
        # 5b) Check for raw tcp mode.
        very_likely_http = context.client.alpn and context.client.alpn in HTTP_ALPNS
        probably_no_http = not very_likely_http and (
            # the first three bytes should be the HTTP verb, so A-Za-z is expected.
            len(data_client) < 3
            or not data_client[:3].isalpha()
            # a server greeting would be uncharacteristic.
            or data_server
        )
        if ctx.options.rawtcp and probably_no_http:
            return layers.TCPLayer(context)
        # 5c) Assume HTTP by default.
        return layers.HttpLayer(context, HTTPMode.transparent)

    def _ignore_connection(
        self,
        context: Context,
        data_client: bytes,
    ) -> bool | None:
        """
        Returns:
            True, if the connection should be ignored.
            False, if it should not be ignored.

        Raises:
            NeedsMoreData, if we need to wait for more input data.
        """
        if not ctx.options.ignore_hosts and not ctx.options.allow_hosts:
            return False

        hostnames: list[str] = []
        if context.server.peername and (peername := context.server.peername[0]):
            hostnames.append(peername)
        if context.server.address and (server_address := context.server.address[0]):
            hostnames.append(server_address)
        if (
            client_hello := self._get_client_hello(context, data_client)
        ) and client_hello.sni:
            hostnames.append(client_hello.sni)

        if not hostnames:
            return False

        if ctx.options.ignore_hosts:
            return any(
                re.search(rex, host, re.IGNORECASE)
                for host in hostnames
                for rex in ctx.options.ignore_hosts
            )
        elif ctx.options.allow_hosts:
            return not any(
                re.search(rex, host, re.IGNORECASE)
                for host in hostnames
                for rex in ctx.options.allow_hosts
            )
        else:  # pragma: no cover
            raise AssertionError()

    def _get_client_hello(
        self, context: Context, data_client: bytes
    ) -> ClientHello | None:
        """
        Try to read a TLS/DTLS/QUIC ClientHello from data_client.

        Returns:
            A complete ClientHello, or None, if no ClientHello was found.

        Raises:
            NeedsMoreData, if the ClientHello is incomplete.
        """
        match context.client.transport_protocol:
            case "tcp":
                if starts_like_tls_record(data_client):
                    try:
                        ch = parse_client_hello(data_client)
                    except ValueError:
                        pass
                    else:
                        if ch is None:
                            raise NeedsMoreData
                        return ch
                return None
            case "udp":
                try:
                    return quic_parse_client_hello(data_client)
                except ValueError:
                    pass

                try:
                    ch = dtls_parse_client_hello(data_client)
                except ValueError:
                    pass
                else:
                    if ch is None:
                        raise NeedsMoreData
                    return ch
                return None
            case _:  # pragma: no cover
                assert_never(context.client.transport_protocol)

    def _setup_reverse_proxy(self, context: Context, data_client: bytes) -> Layer:
        spec = cast(mode_specs.ReverseMode, context.client.proxy_mode)
        stack = tunnel.LayerStack()

        match spec.scheme:
            case "http":
                if starts_like_tls_record(data_client):
                    stack /= ClientTLSLayer(context)
                stack /= HttpLayer(context, HTTPMode.transparent)
            case "https":
                stack /= ServerTLSLayer(context)
                if starts_like_tls_record(data_client):
                    stack /= ClientTLSLayer(context)
                stack /= HttpLayer(context, HTTPMode.transparent)

            case "tcp":
                if starts_like_tls_record(data_client):
                    stack /= ClientTLSLayer(context)
                stack /= TCPLayer(context)
            case "tls":
                stack /= ServerTLSLayer(context)
                if starts_like_tls_record(data_client):
                    stack /= ClientTLSLayer(context)
                stack /= TCPLayer(context)

            case "udp":
                if starts_like_dtls_record(data_client):
                    stack /= ClientTLSLayer(context)
                stack /= UDPLayer(context)
            case "dtls":
                stack /= ServerTLSLayer(context)
                if starts_like_dtls_record(data_client):
                    stack /= ClientTLSLayer(context)
                stack /= UDPLayer(context)

            case "dns":
                # TODO: DNS-over-TLS / DNS-over-DTLS
                # is_tls_or_dtls = (
                #     context.client.transport_protocol == "tcp" and starts_like_tls_record(data_client)
                #     or
                #     context.client.transport_protocol == "udp" and starts_like_dtls_record(data_client)
                # )
                # if is_tls_or_dtls:
                #     stack /= ClientTLSLayer(context)
                stack /= DNSLayer(context)

            case "http3":
                stack /= ServerQuicLayer(context)
                stack /= ClientQuicLayer(context)
                stack /= HttpLayer(context, HTTPMode.transparent)
            case "quic":
                stack /= ServerQuicLayer(context)
                stack /= ClientQuicLayer(context)
                stack /= RawQuicLayer(context)

            case _:  # pragma: no cover
                assert_never(spec.scheme)

        return stack[0]

    def _setup_explicit_http_proxy(self, context: Context, data_client: bytes) -> Layer:
        stack = tunnel.LayerStack()

        if context.client.transport_protocol == "udp":
            stack /= layers.ClientQuicLayer(context)
        elif starts_like_tls_record(data_client):
            stack /= layers.ClientTLSLayer(context)

        if isinstance(context.layers[0], modes.HttpUpstreamProxy):
            stack /= layers.HttpLayer(context, HTTPMode.upstream)
        else:
            stack /= layers.HttpLayer(context, HTTPMode.regular)

        return stack[0]

    def _is_destination_in_hosts(
        self, context: Context, hosts: Iterable[re.Pattern]
    ) -> bool:
        return any(
            (context.server.address and rex.search(context.server.address[0]))
            or (context.client.sni and rex.search(context.client.sni))
            for rex in hosts
        )


def _starts_like_quic(data_client: bytes) -> bool:
    # FIXME: handle clienthellos distributed over multiple packets?
    # FIXME: perf
    try:
        quic_parse_client_hello(data_client)
    except ValueError:
        return False
    else:
        return True
