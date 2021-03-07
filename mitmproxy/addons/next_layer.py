import re
from typing import Type, Sequence, Union, Tuple, Any, Iterable, Optional, List

from mitmproxy import ctx, exceptions, connection
from mitmproxy.net.tls import is_tls_record_magic
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy import context, layer, layers
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers.tls import HTTP_ALPNS, parse_client_hello

LayerCls = Type[layer.Layer]


def stack_match(
        context: context.Context,
        layers: Sequence[Union[LayerCls, Tuple[LayerCls, ...]]]
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

    def configure(self, updated):
        if "tcp_hosts" in updated:
            self.tcp_hosts = [
                re.compile(x, re.IGNORECASE) for x in ctx.options.tcp_hosts
            ]
        if "allow_hosts" in updated or "ignore_hosts" in updated:
            if ctx.options.allow_hosts and ctx.options.ignore_hosts:
                raise exceptions.OptionsError("The allow_hosts and ignore_hosts options are mutually exclusive.")
            self.ignore_hosts = [
                re.compile(x, re.IGNORECASE) for x in ctx.options.ignore_hosts
            ]
            self.allow_hosts = [
                re.compile(x, re.IGNORECASE) for x in ctx.options.allow_hosts
            ]

    def ignore_connection(self, server_address: Optional[connection.Address], data_client: bytes) -> Optional[bool]:
        """
        Returns:
            True, if the connection should be ignored.
            False, if it should not be ignored.
            None, if we need to wait for more input data.
        """
        if not ctx.options.ignore_hosts and not ctx.options.allow_hosts:
            return False

        hostnames: List[str] = []
        if server_address is not None:
            hostnames.append(server_address[0])
        if is_tls_record_magic(data_client):
            try:
                ch = parse_client_hello(data_client)
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

    def next_layer(self, nextlayer: layer.NextLayer):
        nextlayer.layer = self._next_layer(
            nextlayer.context,
            nextlayer.data_client(),
            nextlayer.data_server(),
        )

    def _next_layer(self, context: context.Context, data_client: bytes, data_server: bytes) -> Optional[layer.Layer]:
        if len(context.layers) == 0:
            return self.make_top_layer(context)

        if len(data_client) < 3 and not data_server:
            return None

        client_tls = is_tls_record_magic(data_client)

        def s(*layers):
            return stack_match(context, layers)

        top_layer = context.layers[-1]

        # 1. check for --ignore/--allow
        ignore = self.ignore_connection(context.server.address, data_client)
        if ignore is True:
            return layers.TCPLayer(context, ignore=True)
        if ignore is None:
            return None

        # 2. Check for TLS
        if client_tls:
            # client tls requires a server tls layer as parent layer
            # reverse proxy mode manages this itself.
            # a secure web proxy doesn't have a server part.
            if isinstance(top_layer, layers.ServerTLSLayer) or s(modes.ReverseProxy) or s(modes.HttpProxy):
                return layers.ClientTLSLayer(context)
            else:
                return layers.ServerTLSLayer(context)

        # 3. Setup the HTTP layer for a regular HTTP proxy or an upstream proxy.
        if any([
            s(modes.HttpProxy),
            # or a "Secure Web Proxy", see https://www.chromium.org/developers/design-documents/secure-web-proxy
            s(modes.HttpProxy, layers.ClientTLSLayer),
        ]):
            if ctx.options.mode == "regular":
                return layers.HttpLayer(context, HTTPMode.regular)
            else:
                return layers.HttpLayer(context, HTTPMode.upstream)

        # 4. Check for --tcp
        if any(
                (context.server.address and rex.search(context.server.address[0])) or
                (context.client.sni and rex.search(context.client.sni))
                for rex in self.tcp_hosts
        ):
            return layers.TCPLayer(context)

        # 5. Check for raw tcp mode.
        very_likely_http = (
                context.client.alpn and context.client.alpn in HTTP_ALPNS
        )
        probably_no_http = not very_likely_http and (
                not data_client[:3].isalpha()  # the first three bytes should be the HTTP verb, so A-Za-z is expected.
                or data_server  # a server greeting would be uncharacteristic.
        )
        if ctx.options.rawtcp and probably_no_http:
            return layers.TCPLayer(context)

        # 6. Assume HTTP by default.
        return layers.HttpLayer(context, HTTPMode.transparent)

    def make_top_layer(self, context: context.Context) -> layer.Layer:
        if ctx.options.mode == "regular" or ctx.options.mode.startswith("upstream:"):
            return layers.modes.HttpProxy(context)

        elif ctx.options.mode == "transparent":
            return layers.modes.TransparentProxy(context)

        elif ctx.options.mode.startswith("reverse:"):
            return layers.modes.ReverseProxy(context)

        elif ctx.options.mode == "socks5":
            return layers.modes.Socks5Proxy(context)

        else:  # pragma: no cover
            raise AssertionError("Unknown mode.")
