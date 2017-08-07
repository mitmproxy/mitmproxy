from mitmproxy import ctx
from mitmproxy.net import server_spec
from mitmproxy.proxy.config import HostMatcher
from mitmproxy.proxy.protocol import is_tls_record_magic
from mitmproxy.proxy2 import layer, layers


class NextLayer:
    check_tcp: HostMatcher

    def __init__(self):
        self.check_tcp = HostMatcher()

    def configure(self, updated):
        if "tcp_hosts" in updated:
            self.check_tcp = HostMatcher(ctx.options.tcp_hosts)

    def next_layer(self, nextlayer: layer.NextLayer):
        top_layer = nextlayer.context.layers[-1]
        data_client = nextlayer.data_client()

        if len(data_client) < 3:
            return

        client_tls = is_tls_record_magic(data_client)

        # 1. check for --ignore
        # TODO

        # 2. Always insert a TLS layer as second layer, even if there's neither client nor server
        # tls. An addon may upgrade from http to https, in which case we need a TLS layer.
        if isinstance(top_layer, layers.modes.ReverseProxy):
            nextlayer.context.client.tls = client_tls
            nextlayer.context.server.tls = (
                server_spec.parse_with_mode(ctx.options.mode)[1].scheme == "https"
            )
            nextlayer.layer = layers.TLSLayer(nextlayer.context)
            return
        # TODO: Other top layers

        # 3. In Http Proxy mode and Upstream Proxy mode, the next layer is fixed.
        # TODO

        # 4. Check for other TLS cases (e.g. after CONNECT).
        if client_tls:
            nextlayer.context.client.tls = True
            nextlayer.context.server.tls = True
            nextlayer.layer = layers.TLSLayer(nextlayer.context)
            return

        # 5. Check for --tcp
        if self.check_tcp(nextlayer.context.server.address):
            nextlayer.layer = layers.TCPLayer(nextlayer.context)
            return

        # 6. Check for TLS ALPN (HTTP1/HTTP2)
        if isinstance(top_layer, layers.TLSLayer):
            alpn = nextlayer.context.client.alpn
            if alpn == b'http/1.1':
                nextlayer.layer = layers.HTTPLayer(nextlayer.context)
                return
                # TODO

        pass
        # 7. Check for raw tcp mode
        # TODO

        # 8. Assume HTTP1 by default
        nextlayer.layer = layers.HTTPLayer(nextlayer.context)
        return
