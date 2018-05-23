from mitmproxy import ctx
from mitmproxy.net.tls import is_tls_record_magic
from mitmproxy.proxy.config import HostMatcher
from mitmproxy.proxy2 import layer, layers, context
from mitmproxy.proxy2.layers.glue import GLUE_DEBUG


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

        # 1. check for --ignore
        if ctx.options.ignore_hosts:
            raise NotImplementedError()

        # 2. Always insert a TLS layer as second layer, even if there's neither client nor server
        # tls. An addon may upgrade from http to https, in which case we need a TLS layer.
        if len(context.layers) == 1:
            if ctx.options.mode == "regular" or ctx.options.mode.startswith("reverse:"):
                if client_tls:
                    return layers.ClientTLSLayer(context)
                else:
                    return layers.ServerTLSLayer(context)
            else:
                raise NotImplementedError()

        # 3. In Http Proxy mode and Upstream Proxy mode, the next layer is fixed.
        if len(context.layers) == 2:
            if ctx.options.mode == "regular":
                return layers.GlueLayer(context)  # TODO

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
                return layers.GlueLayer(context)  # TODO
                # return layers.HTTPLayer(context, HTTPMode.transparent)
            elif alpn == b"http/2":
                return layers.GlueLayer(context)  # TODO

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
