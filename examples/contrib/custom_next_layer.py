"""
This addon demonstrates how to override next_layer to modify the protocol in use.
In this example, we are forcing connections to example.com:443 to instead go as plaintext
to example.com:80.

Example usage:

    - mitmdump -s custom_next_layer.py
    - curl -x localhost:8080 -k https://example.com
"""
from mitmproxy import ctx
from mitmproxy.proxy import layer, layers


def running():
    # We change the connection strategy to lazy so that next_layer happens before we actually connect upstream.
    # Alternatively we could also change the server address in `server_connect`.
    ctx.options.connection_strategy = "lazy"


def next_layer(nextlayer: layer.NextLayer):
    ctx.log(
        f"{nextlayer.context=}\n"
        f"{nextlayer.data_client()[:70]=}\n"
        f"{nextlayer.data_server()[:70]=}\n"
    )

    if nextlayer.context.server.address == ("example.com", 443):
        nextlayer.context.server.address = ("example.com", 80)

        # We are disabling ALPN negotiation as our curl client would otherwise agree on HTTP/2,
        # which our example server here does not accept for plaintext connections.
        nextlayer.context.client.alpn = b""

        # We know all layers that come next: First negotiate TLS with the client, then do simple TCP passthrough.
        # Setting only one layer here would also work, in that case next_layer would be called again after TLS establishment.
        nextlayer.layer = layers.ClientTLSLayer(nextlayer.context)
        nextlayer.layer.child_layer = layers.TCPLayer(nextlayer.context)
