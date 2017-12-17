import io
import uuid

from mitmproxy.net import websockets
from mitmproxy.test import tutils
from mitmproxy import tcp
from mitmproxy import websocket
from mitmproxy import controller
from mitmproxy import http
from mitmproxy import connections
from mitmproxy import flow
from mitmproxy.net import http as net_http


def ttcpflow(client_conn=True, server_conn=True, messages=True, err=None):
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if messages is True:
        messages = [
            tcp.TCPMessage(True, b"hello"),
            tcp.TCPMessage(False, b"it's me"),
        ]
    if err is True:
        err = terr()

    f = tcp.TCPFlow(client_conn, server_conn)
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
            timestamp_start=1,
            timestamp_end=2,
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
            timestamp_start=1,
            timestamp_end=2,
            content=b'',
        )
        handshake_flow = http.HTTPFlow(client_conn, server_conn)
        handshake_flow.request = req
        handshake_flow.response = resp

    f = websocket.WebSocketFlow(client_conn, server_conn, handshake_flow)
    handshake_flow.metadata['websocket_flow'] = f

    if messages is True:
        messages = [
            websocket.WebSocketMessage(websockets.OPCODE.BINARY, True, b"hello binary"),
            websocket.WebSocketMessage(websockets.OPCODE.TEXT, True, "hello text".encode()),
            websocket.WebSocketMessage(websockets.OPCODE.TEXT, False, "it's me".encode()),
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
        ssl_established=False,
        timestamp_start=1,
        timestamp_ssl_setup=2,
        timestamp_end=3,
        sni="address",
        cipher_name="cipher",
        alpn_proto_negotiated=b"http/1.1",
        tls_version="TLSv1.2",
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
        timestamp_start=1,
        timestamp_tcp_setup=2,
        timestamp_ssl_setup=3,
        timestamp_end=4,
        ssl_established=False,
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
