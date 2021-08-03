import uuid

from mitmproxy import connection
from mitmproxy import controller
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import websocket
from mitmproxy.test.tutils import treq, tresp
from wsproto.frame_protocol import Opcode


def ttcpflow(client_conn=True, server_conn=True, messages=True, err=None) -> tcp.TCPFlow:
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


def twebsocketflow(messages=True, err=None, close_code=None, close_reason='') -> http.HTTPFlow:
    flow = http.HTTPFlow(tclient_conn(), tserver_conn())
    flow.request = http.Request(
        "example.com",
        80,
        b"GET",
        b"http",
        b"example.com",
        b"/ws",
        b"HTTP/1.1",
        headers=http.Headers(
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
    flow.response = http.Response(
        b"HTTP/1.1",
        101,
        reason=b"Switching Protocols",
        headers=http.Headers(
            connection='upgrade',
            upgrade='websocket',
            sec_websocket_accept=b'',
        ),
        content=b'',
        trailers=None,
        timestamp_start=946681202,
        timestamp_end=946681203,
    )
    flow.websocket = websocket.WebSocketData()

    if messages is True:
        flow.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203),
            websocket.WebSocketMessage(Opcode.TEXT, True, b"hello text", 946681204),
            websocket.WebSocketMessage(Opcode.TEXT, False, b"it's me", 946681205),
        ]

    flow.websocket.close_reason = close_reason

    if close_code is not None:
        flow.websocket.close_code = close_code
    else:
        if err is True:
            # ABNORMAL_CLOSURE
            flow.websocket.close_code = 1006
        else:
            # NORMAL_CLOSURE
            flow.websocket.close_code = 1000

    flow.reply = controller.DummyReply()
    return flow


def tflow(client_conn=True, server_conn=True, req=True, resp=None, err=None) -> http.HTTPFlow:
    """
    @type client_conn: bool | None | mitmproxy.proxy.connection.ClientConnection
    @type server_conn: bool | None | mitmproxy.proxy.connection.ServerConnection
    @type req:         bool | None | mitmproxy.proxy.protocol.http.Request
    @type resp:        bool | None | mitmproxy.proxy.protocol.http.Response
    @type err:         bool | None | mitmproxy.proxy.protocol.primitives.Error
    @return:           mitmproxy.proxy.protocol.http.HTTPFlow
    """
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if req is True:
        req = treq()
    if resp is True:
        resp = tresp()
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


def tdummyflow(client_conn=True, server_conn=True, err=None) -> DummyFlow:
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


def tclient_conn() -> connection.Client:
    c = connection.Client.from_state(dict(
        id=str(uuid.uuid4()),
        address=("127.0.0.1", 22),
        mitmcert=None,
        tls_established=True,
        timestamp_start=946681200,
        timestamp_tls_setup=946681201,
        timestamp_end=946681206,
        sni="address",
        cipher_name="cipher",
        alpn=b"http/1.1",
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
    c.reply = controller.DummyReply()  # type: ignore
    return c


def tserver_conn() -> connection.Server:
    c = connection.Server.from_state(dict(
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
        alpn=None,
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
    c.reply = controller.DummyReply()  # type: ignore
    return c


def terr(content: str = "error") -> flow.Error:
    err = flow.Error(content, 946681207)
    return err
