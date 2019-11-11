import re
import typing

from mitmproxy import ctx, exceptions
from mitmproxy.net.tls import is_tls_record_magic
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import context, layer, layers
from mitmproxy.proxy2.layers import modes
from mitmproxy.proxy2.layers.tls import HTTP_ALPNS, parse_client_hello

LayerCls = typing.Type[layer.Layer]


def stack_match(
        context: context.Context,
        layers: typing.List[typing.Union[LayerCls, typing.Tuple[LayerCls, ...]]]
) -> bool:
    if len(context.layers) != len(layers):
        return False
    return all(
        expected is typing.Any or isinstance(actual, expected)
        for actual, expected in zip(context.layers, layers)
    )


class HostMatcher:
    def __init__(self, patterns: typing.Iterable[str] = tuple()):
        self.patterns = patterns
        self.regexes = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def __call__(self, address):
        if not address:
            return False
        host = f"{address[0]}:{address[1]}"
        return any(rex.search(host) for rex in self.regexes)

    def __bool__(self):
        return bool(self.patterns)


class NextLayer:
    ignore_hosts: typing.Iterable[re.Pattern] = ()
    allow_hosts: typing.Iterable[re.Pattern] = ()
    tcp_hosts: typing.Iterable[re.Pattern] = ()

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

    def ignore_connection(self, context: context.Context, data_client: bytes) -> typing.Optional[bool]:
        if not ctx.options.ignore_hosts and not ctx.options.allow_hosts:
            return False

        addresses: typing.List[str] = [context.server.address]
        if is_tls_record_magic(data_client):
            try:
                sni = parse_client_hello(data_client).sni
            except ValueError:
                return None  # defer decision, wait for more input data
            else:
                addresses.append(sni.decode("idna"))

        if ctx.options.ignore_hosts:
            return any(
                re.search(rex, address, re.IGNORECASE)
                for address in addresses
                for rex in ctx.options.ignore_hosts
            )
        elif ctx.options.allow_hosts:
            return not any(
                re.search(rex, address, re.IGNORECASE)
                for address in addresses
                for rex in ctx.options.allow_hosts
            )

    def next_layer(self, nextlayer: layer.NextLayer):
        nextlayer.layer = self._next_layer(nextlayer.context, nextlayer.data_client())

    def _next_layer(self, context: context.Context, data_client: bytes) -> typing.Optional[layer.Layer]:
        if len(context.layers) == 0:
            return self.make_top_layer(context)
        if len(context.layers) == 1:
            return layers.ServerTLSLayer(context)

        if len(data_client) < 3:
            return

        client_tls = is_tls_record_magic(data_client)
        s = lambda *layers: stack_match(context, layers)
        top_layer = context.layers[-1]

        # 1. check for --ignore/--allow
        ignore = self.ignore_connection(context, data_client)
        if ignore is True:
            return layers.TCPLayer(context, ignore=True)
        if ignore is None:
            return

        # 2. Check for TLS
        if client_tls:
            # client tls requires a server tls layer as parent layer
            if isinstance(top_layer, layers.ServerTLSLayer):
                return layers.ClientTLSLayer(context)
            else:
                if not s(modes.HttpProxy):
                    # A "Secure Web Proxy" (https://www.chromium.org/developers/design-documents/secure-web-proxy)
                    # This does not imply TLS on the server side.
                    pass
                else:
                    # In all other cases, client TLS implies TLS for both ends.
                    context.server.tls = True
                return layers.ServerTLSLayer(context)

        # 3. Setup the HTTP layer for a regular HTTP proxy or an upstream proxy.
        if any([
            s(modes.HttpProxy, layers.ServerTLSLayer),
            s(modes.HttpProxy, layers.ServerTLSLayer, layers.ClientTLSLayer),
        ]):
            return layers.HTTPLayer(context, HTTPMode.regular)
        if ctx.options.mode.startswith("upstream:") and len(context.layers) <= 3 and isinstance(top_layer,
                                                                                                layers.ServerTLSLayer):
            raise NotImplementedError()

        # 4. Check for --tcp
        if any(
                address and re.search(rex, address, re.IGNORECASE)
                for address in (context.server.address, context.client.sni)
                for rex in ctx.options.allow_hosts
        ):
            return layers.TCPLayer(context)

        # 5. Check for raw tcp mode.
        sni_indicates_non_http = (
                context.client.sni and context.client.sni not in HTTP_ALPNS
        )
        # Very simple heuristic here - the first three bytes should be
        # the HTTP verb, so A-Za-z is expected.
        probably_no_http = (
            not data_client[:3].isalpha()
        )
        if ctx.options.rawtcp and (sni_indicates_non_http or probably_no_http):
            return layers.TCPLayer(context)

        # 6. Assume HTTP by default.
        return layers.HTTPLayer(context, HTTPMode.transparent)

    def make_top_layer(self, context: context.Context) -> layer.Layer:
        if ctx.options.mode == "regular":
            return layers.modes.HttpProxy(context)
        elif ctx.options.mode == "transparent":
            raise NotImplementedError("Mode not implemented.")
        elif ctx.options.mode == "socks5":
            raise NotImplementedError("Mode not implemented.")
        elif ctx.options.mode.startswith("reverse:"):
            return layers.modes.ReverseProxy(context)
        elif ctx.options.mode.startswith("upstream:"):
            raise NotImplementedError("Mode not implemented.")
        else:
            raise NotImplementedError("Unknown mode.")
