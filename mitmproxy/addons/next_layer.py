import functools
import typing

from mitmproxy import ctx, log
from mitmproxy.net.tls import is_tls_record_magic
from mitmproxy.proxy.config import HostMatcher
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import layer, layers, context
from mitmproxy.proxy2.layers import modes
from mitmproxy.proxy2.layers.glue import GLUE_DEBUG

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


class NextLayer:
    check_tcp: HostMatcher

    def __init__(self):
        self.check_tcp = HostMatcher()

    def configure(self, updated):
        if "tcp_hosts" in updated:
            self.check_tcp = HostMatcher(ctx.options.tcp_hosts)

    def next_layer(self, nextlayer: layer.NextLayer):
        if not isinstance(nextlayer, layer.NextLayer):
            if GLUE_DEBUG:
                print(f"[glue: skipping nextlayer for {nextlayer}]")
            return
        nextlayer.layer = self._next_layer(nextlayer, nextlayer.context)

    def _next_layer(self, nextlayer: layer.NextLayer, context: context.Context):
        # 0. New connection
        if not context.layers:
            return self.make_top_layer(context)

        top_layer = context.layers[-1]
        data_client = nextlayer.data_client()
        if len(data_client) < 3:
            return

        client_tls = is_tls_record_magic(data_client)
        s = lambda *layers: stack_match(context, layers)

        # 1. check for --ignore
        if ctx.options.ignore_hosts:
            raise NotImplementedError()

        # 2. Always insert a TLS layer as second layer, even if there's neither client nor server
        # tls. An addon may upgrade from http to https, in which case we need a TLS layer.
        if s((modes.HttpProxy, modes.ReverseProxy)):
            if client_tls:
                # For HttpProxy, this is a "Secure Web Proxy" (https://www.chromium.org/developers/design-documents/secure-web-proxy)
                return layers.ClientTLSLayer(context)
            else:
                return layers.ServerTLSLayer(context)
        elif len(context.layers) == 1:
            raise NotImplementedError()

        # 3. Setup the first HTTP layer for a regular HTTP proxy or an upstream proxy.
        if any([
            s(modes.HttpProxy, layers.ServerTLSLayer),
            s(modes.HttpProxy, layers.ClientTLSLayer, layers.ServerTLSLayer),
        ]):
            return layers.HTTPLayer(context, HTTPMode.regular)

        if ctx.options.mode.startswith("upstream:") and len(context.layers) <= 3 and isinstance(top_layer, layers.ServerTLSLayer):
            raise NotImplementedError()

        # 4. Check for other TLS cases (e.g. after CONNECT).
        if client_tls:
            context.server.tls = True
            return layers.ClientTLSLayer(context)

        # 5. Check for --tcp
        if self.check_tcp(context.server.address):
            return layers.TCPLayer(context)

        # 6. Check for TLS ALPN (HTTP1/HTTP2)
        if isinstance(top_layer, layers.ServerTLSLayer):
            alpn = context.client.alpn
            if alpn == b'http/1.1':
                return layers.HTTPLayer(context, HTTPMode.transparent)
            elif alpn == b"h2":
                return layers.ClientHTTP2Layer(context)

        # 7. Check for raw tcp mode. Very simple heuristic here - the first three bytes should be
        # the HTTP verb, so A-Za-z is expected.
        maybe_http = data_client[:3].isalpha()
        if ctx.options.rawtcp and not maybe_http:
            return layers.TCPLayer(context)

        # 8. Assume HTTP1 by default.
        return layers.GlueLayer(context)  # TODO
        # return layers.HTTPLayer(context, HTTPMode.transparent)

    def make_top_layer(self, context):
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
            raise NotImplementedError("Mode not implemented.")
