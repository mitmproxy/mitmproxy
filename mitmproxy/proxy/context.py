from typing import List, TYPE_CHECKING

from mitmproxy import connection
from mitmproxy.options import Options

if TYPE_CHECKING:
    import mitmproxy.proxy.layer


class Context:
    """
    The context object provided to each `mitmproxy.proxy.layer.Layer` by its parent layer.
    """

    client: connection.Client
    server: connection.Server
    options: Options
    layers: List["mitmproxy.proxy.layer.Layer"]

    def __init__(
        self,
        client: connection.Client,
        options: Options,
    ) -> None:
        self.client = client
        self.options = options
        self.server = connection.Server(None)
        self.layers = []

    def fork(self) -> "Context":
        ret = Context(self.client, self.options)
        ret.server = self.server
        ret.layers = self.layers.copy()
        return ret
