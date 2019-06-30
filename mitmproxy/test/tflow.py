import io
import uuid

from mitmproxy.net import websockets
from mitmproxy.test import tutils
from mitmproxy import tcp
from mitmproxy import websocket
from mitmproxy import controller
from mitmproxy import http
from mitmproxy import http2
from hpack.table import HeaderTable
from mitmproxy import connections
from mitmproxy import flow
from mitmproxy.net import http as net_http


def ttcpflow(client_conn=True, server_conn=True, messages=True, err=None):
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    f = tcp.TCPFlow(client_conn, server_conn)
    if messages is True:
        messages = [
            tcp.TCPMessage(True, b"hello", f),
            tcp.TCPMessage(False, b"it's me", f),
        ]
    if err is True:
        err = terr()

    f.messages = messages
    f.error = err
    f.reply = controller.DummyReply()
    return f


def twebsocketflow(client_conn=True, server_conn=True, messages=True, err=None, handshake_flow=True):

    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if handshake_flow is True:
        req = http.HTTPRequest(
            "relative",
            "GET",
            "http",
            "example.com",
            80,
            "/ws",
            "HTTP/1.1",
            headers=net_http.Headers(
                connection="upgrade",
                upgrade="websocket",
                sec_websocket_version="13",
                sec_websocket_key="1234",
            ),
            timestamp_start=946681200,
            timestamp_end=946681201,
            content=b''
        )
        resp = http.HTTPResponse(
            "HTTP/1.1",
            101,
            reason=net_http.status_codes.RESPONSES.get(101),
            headers=net_http.Headers(
                connection='upgrade',
                upgrade='websocket',
                sec_websocket_accept=b'',
            ),
            timestamp_start=946681202,
            timestamp_end=946681203,
            content=b'',
        )
        handshake_flow = http.HTTPFlow(client_conn, server_conn)
        handshake_flow.request = req
        handshake_flow.response = resp

    f = websocket.WebSocketFlow(client_conn, server_conn, handshake_flow)
    f.metadata['websocket_handshake'] = handshake_flow.id
    handshake_flow.metadata['websocket_flow'] = f.id
    handshake_flow.metadata['websocket'] = True

    if messages is True:
        messages = [
            websocket.WebSocketMessage(websockets.OPCODE.BINARY, True, b"hello binary", f),
            websocket.WebSocketMessage(websockets.OPCODE.TEXT, True, "hello text".encode(), f),
            websocket.WebSocketMessage(websockets.OPCODE.TEXT, False, "it's me".encode(), f),
        ]
    if err is True:
        err = terr()

    f.messages = messages
    f.error = err
    f.reply = controller.DummyReply()
    return f


def thttp2flow(client_conn=True, server_conn=True, messages=True, err=None):
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    f = http2.HTTP2Flow(client_conn, server_conn)
    if messages is True:
        headers = [(b':method', b'GET'),
                   (b':path', b'/?q=&t=h_'),
                   (b':scheme', b'https'),
                   (b'accept', memoryview(b'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')),
                   (b'accept-encoding', b'gzip, deflate, br'),
                   (memoryview(b'upgrade-insecure-requests'), b'1'),
                   (b'cache-control', b'max-age=0'),
                   (b'te', b'trailers')]
        hpack_info = dict(HeaderTable.STATIC_TABLE,
                          dynamic=((b'accept', memoryview(b'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')),
                                   (b'accept-encoding', b'gzip, deflate, br'),
                                   (memoryview(b'upgrade-insecure-requests'), b'1')))
        priority = dict(weight=200,
                        depends_on=8,
                        exclusive=True)
        settings = {1: dict(original_value=4096, new_value=65536),
                    4: dict(original_value=65535, new_value=131072),
                    5: dict(original_value=16384, new_value=16384)}
        messages = [
            http2.Http2Header(True, headers.copy(), hpack_info.copy(), priority, False, f),
            http2.Http2Push(False, 15, headers.copy(), hpack_info.copy(), f),
            http2.Http2Data(True, b"Hey it's a data", 15, True, f),
            http2.Http2WindowsUpdate(False, 1540201, f),
            http2.Http2Settings(True, settings, False, f),
            http2.Http2Ping(True, b"hello", False, f),
            http2.Http2Ping(False, b"it's me", True, f),
            http2.Http2PriorityUpdate(False, priority, f),
            http2.Http2RstStream(True, 12, True, f),
            http2.Http2Goaway(False, 13, 12, "The error", f)
        ]
    if err is True:
        err = terr()

    f.messages = messages
    f.error = err
    f.reply = controller.DummyReply()
    return f


def tflow(client_conn=True, server_conn=True, req=True, resp=None, err=None):
    """
    @type client_conn: bool | None | mitmproxy.proxy.connection.ClientConnection
    @type server_conn: bool | None | mitmproxy.proxy.connection.ServerConnection
    @type req:         bool | None | mitmproxy.proxy.protocol.http.HTTPRequest
    @type resp:        bool | None | mitmproxy.proxy.protocol.http.HTTPResponse
    @type err:         bool | None | mitmproxy.proxy.protocol.primitives.Error
    @return:           mitmproxy.proxy.protocol.http.HTTPFlow
    """
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if req is True:
        req = tutils.treq()
    if resp is True:
        resp = tutils.tresp()
    if err is True:
        err = terr()

    if req:
        req = http.HTTPRequest.wrap(req)
    if resp:
        resp = http.HTTPResponse.wrap(resp)

    f = http.HTTPFlow(client_conn, server_conn)
    f.request = req
    f.response = resp
    f.error = err
    f.reply = controller.DummyReply()
    return f


class DummyFlow(flow.Flow):
    """A flow that is neither HTTP nor TCP."""

    def __init__(self, client_conn, server_conn, live=None):
        super().__init__("dummy", client_conn, server_conn, live)
        self.flow = self


def tdummyflow(client_conn=True, server_conn=True, err=None):
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if err is True:
        err = terr()

    f = DummyFlow(client_conn, server_conn)
    f.error = err
    f.reply = controller.DummyReply()
    return f


def tclient_conn():
    """
    @return: mitmproxy.proxy.connection.ClientConnection
    """
    c = connections.ClientConnection.from_state(dict(
        id=str(uuid.uuid4()),
        address=("127.0.0.1", 22),
        clientcert=None,
        mitmcert=None,
        tls_established=False,
        timestamp_start=946681200,
        timestamp_tls_setup=946681201,
        timestamp_end=946681206,
        sni="address",
        cipher_name="cipher",
        alpn_proto_negotiated=b"http/1.1",
        tls_version="TLSv1.2",
        tls_extensions=[(0x00, bytes.fromhex("000e00000b6578616d"))],
    ))
    c.reply = controller.DummyReply()
    c.rfile = io.BytesIO()
    c.wfile = io.BytesIO()
    return c


def tserver_conn():
    """
    @return: mitmproxy.proxy.connection.ServerConnection
    """
    c = connections.ServerConnection.from_state(dict(
        id=str(uuid.uuid4()),
        address=("address", 22),
        source_address=("address", 22),
        ip_address=("192.168.0.1", 22),
        cert=None,
        timestamp_start=946681202,
        timestamp_tcp_setup=946681203,
        timestamp_tls_setup=946681204,
        timestamp_end=946681205,
        tls_established=False,
        sni="address",
        alpn_proto_negotiated=None,
        tls_version="TLSv1.2",
        via=None,
    ))
    c.reply = controller.DummyReply()
    c.rfile = io.BytesIO()
    c.wfile = io.BytesIO()
    return c


def terr(content="error"):
    """
    @return: mitmproxy.proxy.protocol.primitives.Error
    """
    err = flow.Error(content)
    return err
