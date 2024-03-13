import weakref
from collections.abc import MutableMapping

from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy import http


class ProxyForwardHeaders:
    def __init__(self) -> None:
        self.connection_headers: MutableMapping[
            connection.Client, tuple[str, str]
        ] = weakref.WeakKeyDictionary()

    def load(self, loader):
        loader.add_option(
            "proxyforwardheaders",
            bool,
            False,
            """
            Forward CONNECT headers to upstream proxy.
            """,
        )

    def http_connect(self, f: http.HTTPFlow) -> None:
        if ctx.options.proxyforwardheaders:
            self.connection_headers[f.client_conn] = f.request.headers

    def http_connect_upstream(self, f: http.HTTPFlow):
        if ctx.options.proxyforwardheaders and self.connection_headers:
            f.request.headers = self.connection_headers[f.client_conn]


addons = [ProxyForwardHeaders()]
