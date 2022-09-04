from typing import TYPE_CHECKING, Optional

from mitmproxy import connection
from mitmproxy.options import Options

if TYPE_CHECKING:
    import mitmproxy.proxy.layer
    from mitmproxy.proxy.server import ConnectionHandler


class Context:
    """
    The context object provided to each protocol layer in the proxy core.
    """

    client: connection.Client
    """The client connection."""
    server: connection.Server
    """
    The server connection.

    For practical reasons this attribute is always set, even if there is not server connection yet.
    In this case the server address is `None`.
    """
    options: Options
    """
    Provides access to options for proxy layers. Not intended for use by addons, use `mitmproxy.ctx.options` instead.
    """
    handler: Optional[ConnectionHandler]
    """
    The `ConnectionHandler` responsible for this context.
    """
    layers: list["mitmproxy.proxy.layer.Layer"]
    """
    The protocol layer stack.
    """

    def __init__(
        self,
        client: connection.Client,
        options: Options,
        handler: Optional[ConnectionHandler] = None,
    ) -> None:
        self.client = client
        self.options = options
        self.handler = handler
        self.server = connection.Server(
            None, transport_protocol=client.transport_protocol
        )
        self.layers = []

    def fork(self) -> "Context":
        ret = Context(self.client, self.options, self.handler)
        ret.server = self.server
        ret.layers = self.layers.copy()
        return ret

    def __repr__(self):
        return (
            f"Context(\n"
            f"  {self.client!r},\n"
            f"  {self.server!r},\n"
            f"  layers=[{self.layers!r}]\n"
            f")"
        )
