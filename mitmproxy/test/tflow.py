import io
import uuid

from mitmproxy.test import tutils
from mitmproxy import tcp
from mitmproxy import websocket
from mitmproxy import controller
from mitmproxy import http
from mitmproxy import flow
from mitmproxy.net import http as net_http
from mitmproxy.utils import compat

from wsproto.frame_protocol import Opcode


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
            "example.com",
            80,
            b"GET",
            b"http",
            b"example.com",
            b"/ws",
            b"HTTP/1.1",
            headers=net_http.Headers(
                connection="upgrade",
                upgrade="websocket",
                sec_websocket_version="13",
                sec_websocket_key="1234",
            ),
            content=b'',
            trailers=None,
            timestamp_start=946681200,
            timestamp_end=946681201,

        )
        resp = http.HTTPResponse(
            b"HTTP/1.1",
            101,
            reason=net_http.status_codes.RESPONSES.get(101),
            headers=net_http.Headers(
                connection='upgrade',
                upgrade='websocket',
                sec_websocket_accept=b'',
            ),
            content=b'',
            trailers=None,
            timestamp_start=946681202,
            timestamp_end=946681203,
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
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary"),
            websocket.WebSocketMessage(Opcode.TEXT, True, b"hello text"),
            websocket.WebSocketMessage(Opcode.TEXT, False, b"it's me"),
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


def tclient_conn() -> compat.Client:
    c = compat.Client.from_state(dict(
        id=str(uuid.uuid4()),
        address=("127.0.0.1", 22),
        mitmcert=None,
        tls_established=True,
        timestamp_start=946681200,
        timestamp_tls_setup=946681201,
        timestamp_end=946681206,
        sni="address",
        cipher_name="cipher",
        alpn_proto_negotiated=b"http/1.1",
        tls_version="TLSv1.2",
        tls_extensions=[(0x00, bytes.fromhex("000e00000b6578616d"))],
        state=0,
        sockname=("", 0),
        error=None,
        tls=False,
        certificate_list=[],
        alpn_offers=[],
        cipher_list=[],
    ))
    c.reply = controller.DummyReply()
    c.rfile = io.BytesIO()
    c.wfile = io.BytesIO()
    return c


def tserver_conn() -> compat.Server:
    c = compat.Server.from_state(dict(
        id=str(uuid.uuid4()),
        address=("address", 22),
        source_address=("address", 22),
        ip_address=("192.168.0.1", 22),
        timestamp_start=946681202,
        timestamp_tcp_setup=946681203,
        timestamp_tls_setup=946681204,
        timestamp_end=946681205,
        tls_established=True,
        sni="address",
        alpn_proto_negotiated=None,
        tls_version="TLSv1.2",
        via=None,
        state=0,
        error=None,
        tls=False,
        certificate_list=[],
        alpn_offers=[],
        cipher_name=None,
        cipher_list=[],
        via2=None,
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
