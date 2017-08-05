from mitmproxy import ctx
from mitmproxy.net import server_spec
from mitmproxy.proxy.protocol import is_tls_record_magic
from mitmproxy.proxy2 import layer, layers


class NextLayer:
    def next_layer(self, nextlayer: layer.NextLayer):
        top_layer = nextlayer.context.layers[-1]
        data_client = nextlayer.data_client()

        if len(data_client) < 3:
            return

        client_tls = is_tls_record_magic(data_client)

        # 1. check for --ignore

        # 2. Always insert a TLS layer as second layer, even if there's neither client nor server
        # tls. An addon may upgrade from http to https, in which case we need a TLS layer.
        if isinstance(top_layer, layers.modes.ReverseProxy):
            if client_tls:
                nextlayer.layer = layers.TLSLayer(
                    nextlayer.context,
                    client_tls,
                    server_spec.parse_with_mode(ctx.options.mode)[1].scheme == "https"
                )
            else:
                # FIXME: TLSLayer doesn't support non-TLS yet, so remove this here once that's in.
                nextlayer.layer = layers.HTTPLayer(
                    nextlayer.context
                )
        # TODO: Other top layers

        pass
        # 3. In Http Proxy mode and Upstream Proxy mode, the next layer is fixed.
        # 4. Check for other TLS cases (e.g. after CONNECT).
        # 5. Check for --tcp
        # 6. Check for TLS ALPN (HTTP1/HTTP2)
        # 7. Check for raw tcp mode
        # 8. Assume HTTP1 by default
