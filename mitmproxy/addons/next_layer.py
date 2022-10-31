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
from typing import Any, Callable, Iterable, Optional, Union, cast

from mitmproxy import ctx, dns, exceptions, connection
from mitmproxy.net.tls import is_tls_record_magic
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy import context, layer, layers, mode_specs
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers.quic import quic_parse_client_hello
from mitmproxy.proxy.layers.tls import HTTP_ALPNS, dtls_parse_client_hello, parse_client_hello
from mitmproxy.tls import ClientHello

LayerCls = type[layer.Layer]
ClientSecurityLayerCls = Union[type[layers.ClientTLSLayer], type[layers.ClientQuicLayer]]
ServerSecurityLayerCls = Union[type[layers.ServerTLSLayer], type[layers.ServerQuicLayer]]


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

    def setup_tls_layer(
        self,
        context: context.Context,
        client_layer_cls: ClientSecurityLayerCls = layers.ClientTLSLayer,
        server_layer_cls: ServerSecurityLayerCls = layers.ServerTLSLayer,
    ) -> layer.Layer:
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
            or s(modes.ReverseProxy, server_layer_cls)
        ):
            return client_layer_cls(context)
        else:
            # We already assign the next layer here so that the server layer
            # knows that it can safely wait for a ClientHello.
            ret = server_layer_cls(context)
            ret.child_layer = client_layer_cls(context)
            return ret

    def is_destination_in_hosts(self, context: context.Context, hosts: Iterable[re.Pattern]) -> bool:
        return any(
            (context.server.address and rex.search(context.server.address[0]))
            or (context.client.sni and rex.search(context.client.sni))
            for rex in hosts
        )

    def get_http_layer(self, context: context.Context) -> Optional[layers.HttpLayer]:
        def s(*layers):
            return stack_match(context, layers)

        # Setup the HTTP layer for a regular HTTP proxy ...
        if (
            s(modes.HttpProxy)
            or
            # or a "Secure Web Proxy", see https://www.chromium.org/developers/design-documents/secure-web-proxy
            s(modes.HttpProxy, (layers.ClientTLSLayer, layers.ClientQuicLayer))
        ):
            return layers.HttpLayer(context, HTTPMode.regular)
        # ... or an upstream proxy.
        if (
            s(modes.HttpUpstreamProxy)
            or
            s(modes.HttpUpstreamProxy, (layers.ClientTLSLayer, layers.ClientQuicLayer))
        ):
            return layers.HttpLayer(context, HTTPMode.upstream)
        return None

    def detect_udp_tls(self, data_client: bytes) -> Optional[tuple[ClientHello, ClientSecurityLayerCls, ServerSecurityLayerCls]]:
        if len(data_client) == 0:
            return None

        # first try DTLS (the parser may return None)
        try:
            client_hello = dtls_parse_client_hello(data_client)
            if client_hello is not None:
                return (client_hello, layers.ClientTLSLayer, layers.ServerTLSLayer)
        except ValueError:
            pass

        # next try QUIC
        try:
            client_hello = quic_parse_client_hello(data_client)
            return (client_hello, layers.ClientQuicLayer, layers.ServerQuicLayer)
        except (ValueError, TypeError):
            pass

        # that's all we currently have to offer
        return None

    def raw_udp_layer(self, context: context.Context, ignore: bool = False) -> layer.Layer:
        def s(*layers):
            return stack_match(context, layers)

        # for regular and upstream HTTP3, if we already created a client QUIC layer
        # we need a server and raw QUIC layer as well
        if (
            s(modes.HttpProxy, layers.ClientQuicLayer)
            or
            s(modes.HttpUpstreamProxy, layers.ClientQuicLayer)
        ):
            server_layer = layers.ServerQuicLayer(context)
            server_layer.child_layer = layers.RawQuicLayer(context, ignore=ignore)
            return server_layer

        # for reverse HTTP3 and QUIC, we need a client and raw QUIC layer
        elif (s(modes.ReverseProxy, layers.ServerQuicLayer)):
            client_layer = layers.ClientQuicLayer(context)
            client_layer.child_layer = layers.RawQuicLayer(context, ignore=ignore)
            return client_layer

        # in other cases we assume `setup_tls_layer` happened, so if the
        # top layer is `ClientQuicLayer` we return a raw QUIC layer...
        elif isinstance(context.layers[-1], layers.ClientQuicLayer):
            return layers.RawQuicLayer(context, ignore=ignore)

        # ... otherwise an UDP layer
        else:
            return layers.UDPLayer(context, ignore=ignore)

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

        if context.client.transport_protocol == "tcp":
            if (
                len(data_client) < 3
                and not data_server
                and not isinstance(context.layers[-1], layers.QuicStreamLayer)
            ):
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

            # 3. Check for HTTP
            if http_layer := self.get_http_layer(context):
                return http_layer

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
            tls = self.detect_udp_tls(data_client)

            # 1. check for --ignore/--allow
            if self.ignore_connection(
                context.server.address,
                data_client,
                is_tls=lambda _: tls is not None,
                client_hello=lambda _: None if tls is None else tls[0]
            ):
                return self.raw_udp_layer(context, ignore=True)

            # 2. Check for DTLS/QUIC
            if tls is not None:
                _, client_layer_cls, server_layer_cls = tls
                return self.setup_tls_layer(context, client_layer_cls, server_layer_cls)

            # 3. Check for HTTP
            if http_layer := self.get_http_layer(context):
                return http_layer

            # 4. Check for --udp
            if self.is_destination_in_hosts(context, self.udp_hosts):
                return self.raw_udp_layer(context)

            # 5. Check for reverse modes
            if (isinstance(context.layers[0], modes.ReverseProxy)):
                scheme = cast(mode_specs.ReverseMode, context.client.proxy_mode).scheme
                if scheme in ("udp", "dtls"):
                    return layers.UDPLayer(context)
                elif scheme == "http3":
                    return layers.HttpLayer(context, HTTPMode.transparent)
                elif scheme == "quic":
                    # if the client supports QUIC, we use QUIC raw layer,
                    # otherwise we only use the QUIC datagram only
                    return (
                        layers.RawQuicLayer(context)
                        if isinstance(context.layers[-1], layers.ClientQuicLayer) else
                        layers.UDPLayer(context)
                    )
                elif scheme == "dns":
                    return layers.DNSLayer(context)
                else:
                    raise AssertionError(scheme)

            # 6. Check for DNS
            try:
                dns.Message.unpack(data_client)
            except struct.error:
                pass
            else:
                return layers.DNSLayer(context)

            # 7. Use raw mode.
            return self.raw_udp_layer(context)

        else:
            raise AssertionError(context.client.transport_protocol)
