"""
This addon determines the next protocol layer in our proxy stack.
Whenever a protocol layer in the proxy wants to pass a connection to a child layer and isn't sure which protocol comes
next, it calls the `next_layer` hook, which ends up here.
For example, if mitmproxy runs as a regular proxy, we first need to determine if
new clients start with a TLS handshake right away (Secure Web Proxy) or send a plaintext HTTP CONNECT request.
This addon here peeks at the incoming bytes and then makes a decision based on proxy mode, mitmproxy options, etc.

For a typical HTTPS request, this addon is called a couple of times: First to determine that we start with an HTTP layer
which processes the `CONNECT` request, a second time to determine that the client then starts negotiating TLS, and a
third time where we check if the protocol within that TLS stream is actually HTTP or something else.

Sometimes it's useful to hardcode specific logic in next_layer when one wants to do fancy things.
In that case it's not necessary to modify mitmproxy's source, adding a custom addon with a next_layer event hook
that sets nextlayer.layer works just as well.
"""
import re
from collections.abc import Sequence
import struct
from typing import Any, Callable, Iterable, Optional, Union

from mitmproxy import ctx, dns, exceptions, connection
from mitmproxy.net.tls import is_tls_record_magic
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy import context, layer, layers
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers.tls import HTTP_ALPNS, dtls_parse_client_hello, parse_client_hello
from mitmproxy.tls import ClientHello

LayerCls = type[layer.Layer]


def stack_match(
    context: context.Context, layers: Sequence[Union[LayerCls, tuple[LayerCls, ...]]]
) -> bool:
    if len(context.layers) != len(layers):
        return False
    return all(
        expected is Any or isinstance(actual, expected)
        for actual, expected in zip(context.layers, layers)
    )


class NextLayer:
    ignore_hosts: Iterable[re.Pattern] = ()
    allow_hosts: Iterable[re.Pattern] = ()
    tcp_hosts: Iterable[re.Pattern] = ()
    udp_hosts: Iterable[re.Pattern] = ()

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

    def ignore_connection(
        self,
        server_address: Optional[connection.Address],
        data_client: bytes,
        *,
        is_tls: Callable[[bytes], bool] = is_tls_record_magic,
        client_hello: Callable[[bytes], Optional[ClientHello]] = parse_client_hello
    ) -> Optional[bool]:
        """
        Returns:
            True, if the connection should be ignored.
            False, if it should not be ignored.
            None, if we need to wait for more input data.
        """
        if not ctx.options.ignore_hosts and not ctx.options.allow_hosts:
            return False

        hostnames: list[str] = []
        if server_address is not None:
            hostnames.append(server_address[0])
        if is_tls(data_client):
            try:
                ch = client_hello(data_client)
                if ch is None:  # not complete yet
                    return None
                sni = ch.sni
            except ValueError:
                pass
            else:
                if sni:
                    hostnames.append(sni)

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

    def setup_tls_layer(self, context: context.Context) -> layer.Layer:
        def s(*layers):
            return stack_match(context, layers)

        # client tls usually requires a server tls layer as parent layer, except:
        #  - a secure web proxy doesn't have a server part.
        #  - an upstream proxy uses the mode spec
        #  - reverse proxy mode manages this itself.
        if (
            s(modes.HttpProxy)
            or s(modes.HttpUpstreamProxy)
            or s(modes.ReverseProxy)
            or s(modes.ReverseProxy, layers.ServerTLSLayer)
        ):
            return layers.ClientTLSLayer(context)
        else:
            # We already assign the next layer here so that ServerTLSLayer
            # knows that it can safely wait for a ClientHello.
            ret = layers.ServerTLSLayer(context)
            ret.child_layer = layers.ClientTLSLayer(context)
            return ret

    def is_destination_in_hosts(self, context: context.Context, hosts: Iterable[re.Pattern]) -> bool:
        return any(
            (context.server.address and rex.search(context.server.address[0]))
            or (context.client.sni and rex.search(context.client.sni))
            for rex in hosts
        )

    def next_layer(self, nextlayer: layer.NextLayer):
        if nextlayer.layer is None:
            nextlayer.layer = self._next_layer(
                nextlayer.context,
                nextlayer.data_client(),
                nextlayer.data_server(),
            )

    def _next_layer(
        self, context: context.Context, data_client: bytes, data_server: bytes
    ) -> Optional[layer.Layer]:
        assert context.layers

        # helper function to quickly check if the existing layer stack matches a particular configuration.
        def s(*layers):
            return stack_match(context, layers)

        if context.client.transport_protocol == "tcp":
            if len(data_client) < 3 and not data_server:
                return None  # not enough data yet to make a decision

            # 1. check for --ignore/--allow
            ignore = self.ignore_connection(context.server.address, data_client)
            if ignore is True:
                return layers.TCPLayer(context, ignore=True)
            if ignore is None:
                return None

            # 2. Check for TLS
            if is_tls_record_magic(data_client):
                return self.setup_tls_layer(context)

            # 3. Setup the HTTP layer for a regular HTTP proxy
            if (
                s(modes.HttpProxy)
                or
                # or a "Secure Web Proxy", see https://www.chromium.org/developers/design-documents/secure-web-proxy
                s(modes.HttpProxy, layers.ClientTLSLayer)
            ):
                return layers.HttpLayer(context, HTTPMode.regular)
            # 3b. ... or an upstream proxy.
            if (
                s(modes.HttpUpstreamProxy)
                or
                s(modes.HttpUpstreamProxy, layers.ClientTLSLayer)
            ):
                return layers.HttpLayer(context, HTTPMode.upstream)

            # 4. Check for --tcp
            if self.is_destination_in_hosts(context, self.tcp_hosts):
                return layers.TCPLayer(context)

            # 5. Check for raw tcp mode.
            very_likely_http = context.client.alpn and context.client.alpn in HTTP_ALPNS
            probably_no_http = not very_likely_http and (
                not data_client[
                    :3
                ].isalpha()  # the first three bytes should be the HTTP verb, so A-Za-z is expected.
                or data_server  # a server greeting would be uncharacteristic.
            )
            if ctx.options.rawtcp and probably_no_http:
                return layers.TCPLayer(context)

            # 6. Assume HTTP by default.
            return layers.HttpLayer(context, HTTPMode.transparent)

        elif context.client.transport_protocol == "udp":
            # unlike TCP, we make a decision immediately
            try:
                dtls_client_hello = dtls_parse_client_hello(data_client)
            except ValueError:
                dtls_client_hello = None

            # 1. check for --ignore/--allow
            if self.ignore_connection(
                context.server.address,
                data_client,
                is_tls=lambda _: dtls_client_hello is not None,
                client_hello=lambda _: dtls_client_hello
            ):
                return layers.UDPLayer(context, ignore=True)

            # 2. Check for DTLS
            if dtls_client_hello is not None:
                return self.setup_tls_layer(context)

            # 3. (skipped for now, until we support HTTP/3)

            # 4. Check for --udp
            if self.is_destination_in_hosts(context, self.udp_hosts):
                return layers.UDPLayer(context)

            # 5. Check for DNS
            try:
                dns.Message.unpack(data_client)
            except struct.error:
                pass
            else:
                return layers.DNSLayer(context)

            # 6. Check for raw udp mode.
            if ctx.options.rawudp:
                return layers.UDPLayer(context)

            # 7. Ignore the connection by default. (In the future, we'll assume HTTP/3)
            return layers.UDPLayer(context, ignore=True)

        else:
            raise AssertionError(context.client.transport_protocol)
