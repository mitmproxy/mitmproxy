from aioquic.h3.connection import H3Connection
from mitmproxy.connection import Connection
from ._base import HttpConnection
from ..quic import QuicLayer
from ...context import Context


class Http3Connection(HttpConnection):
    h3_conn: H3Connection

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context, conn)
        quic = context.layers[0]
        assert isinstance(quic, QuicLayer)
        self.h3_conn = H3Connection(quic.conn)


class Http3Server(Http3Connection):
    def __init__(self, context: Context):
        super().__init__(context, context.client)


class Http3Client(Http3Connection):
    def __init__(self, context: Context):
        super().__init__(context, context.server)


__all__ = [
    "Http3Client",
    "Http3Server",
]
