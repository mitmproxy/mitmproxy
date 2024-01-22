import uuid

from wsproto.frame_protocol import Opcode

from mitmproxy import connection
from mitmproxy import dns
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy import websocket
from mitmproxy.connection import ConnectionState
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.test.tutils import tdnsreq
from mitmproxy.test.tutils import tdnsresp
from mitmproxy.test.tutils import treq
from mitmproxy.test.tutils import tresp


def ttcpflow(
    client_conn=True, server_conn=True, messages=True, err=None
) -> tcp.TCPFlow:
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if messages is True:
        messages = [
            tcp.TCPMessage(True, b"hello", 946681204.2),
            tcp.TCPMessage(False, b"it's me", 946681204.5),
        ]
    if err is True:
        err = terr()

    f = tcp.TCPFlow(client_conn, server_conn)
    f.timestamp_created = client_conn.timestamp_start
    f.messages = messages
    f.error = err
    f.live = True
    return f


def tudpflow(
    client_conn=True, server_conn=True, messages=True, err=None
) -> udp.UDPFlow:
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if messages is True:
        messages = [
            udp.UDPMessage(True, b"hello", 946681204.2),
            udp.UDPMessage(False, b"it's me", 946681204.5),
        ]
    if err is True:
        err = terr()

    f = udp.UDPFlow(client_conn, server_conn)
    f.timestamp_created = client_conn.timestamp_start
    f.messages = messages
    f.error = err
    f.live = True
    return f


def twebsocketflow(
    messages=True, err=None, close_code=None, close_reason=""
) -> http.HTTPFlow:
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
        content=b"",
        trailers=None,
        timestamp_start=946681200,
        timestamp_end=946681201,
    )
    flow.response = http.Response(
        b"HTTP/1.1",
        101,
        reason=b"Switching Protocols",
        headers=http.Headers(
            connection="upgrade",
            upgrade="websocket",
            sec_websocket_accept=b"",
        ),
        content=b"",
        trailers=None,
        timestamp_start=946681202,
        timestamp_end=946681203,
    )

    flow.websocket = twebsocket()

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

    flow.live = True
    return flow


def tdnsflow(
    *,
    client_conn: connection.Client | None = None,
    server_conn: connection.Server | None = None,
    req: dns.Message | None = None,
    resp: bool | dns.Message = False,
    err: bool | flow.Error = False,
    live: bool = True,
) -> dns.DNSFlow:
    """Create a DNS flow for testing."""
    if client_conn is None:
        client_conn = tclient_conn()
        client_conn.proxy_mode = ProxyMode.parse("dns")
        client_conn.transport_protocol = "udp"
    if server_conn is None:
        server_conn = tserver_conn()
        server_conn.transport_protocol = "udp"
    if req is None:
        req = tdnsreq()

    if resp is True:
        resp = tdnsresp()
    if err is True:
        err = terr()

    assert resp is False or isinstance(resp, dns.Message)
    assert err is False or isinstance(err, flow.Error)

    f = dns.DNSFlow(client_conn, server_conn)
    f.timestamp_created = req.timestamp
    f.request = req
    f.response = resp or None
    f.error = err or None
    f.live = live
    return f


def tflow(
    *,
    client_conn: connection.Client | None = None,
    server_conn: connection.Server | None = None,
    req: http.Request | None = None,
    resp: bool | http.Response = False,
    err: bool | flow.Error = False,
    ws: bool | websocket.WebSocketData = False,
    live: bool = True,
) -> http.HTTPFlow:
    """Create a flow for testing."""
    if client_conn is None:
        client_conn = tclient_conn()
    if server_conn is None:
        server_conn = tserver_conn()
    if req is None:
        req = treq()

    if resp is True:
        resp = tresp()
    if err is True:
        err = terr()
    if ws is True:
        ws = twebsocket()

    assert resp is False or isinstance(resp, http.Response)
    assert err is False or isinstance(err, flow.Error)
    assert ws is False or isinstance(ws, websocket.WebSocketData)

    f = http.HTTPFlow(client_conn, server_conn)
    f.timestamp_created = req.timestamp_start
    f.request = req
    f.response = resp or None
    f.error = err or None
    f.websocket = ws or None
    f.live = live
    return f


class DummyFlow(flow.Flow):
    """A flow that is neither HTTP nor TCP."""


def tdummyflow(client_conn=True, server_conn=True, err=None) -> DummyFlow:
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if err is True:
        err = terr()

    f = DummyFlow(client_conn, server_conn)
    f.error = err
    f.live = True
    return f


def tclient_conn() -> connection.Client:
    c = connection.Client(
        id=str(uuid.uuid4()),
        peername=("127.0.0.1", 22),
        sockname=("", 0),
        mitmcert=None,
        timestamp_start=946681200,
        timestamp_tls_setup=946681201,
        timestamp_end=946681206,
        sni="address",
        cipher="cipher",
        alpn=b"http/1.1",
        tls_version="TLSv1.2",
        state=ConnectionState.OPEN,
        error=None,
        tls=False,
        certificate_list=[],
        alpn_offers=[],
        cipher_list=[],
        proxy_mode=ProxyMode.parse("regular"),
    )
    return c


def tserver_conn() -> connection.Server:
    c = connection.Server(
        id=str(uuid.uuid4()),
        address=("address", 22),
        peername=("192.168.0.1", 22),
        sockname=("address", 22),
        timestamp_start=946681202,
        timestamp_tcp_setup=946681203,
        timestamp_tls_setup=946681204,
        timestamp_end=946681205,
        sni="address",
        alpn=None,
        tls_version="TLSv1.2",
        via=None,
        state=ConnectionState.CLOSED,
        error=None,
        tls=False,
        certificate_list=[],
        alpn_offers=[],
        cipher=None,
        cipher_list=[],
    )
    return c


def terr(content: str = "error") -> flow.Error:
    err = flow.Error(content, 946681207)
    return err


def twebsocket(messages: bool = True) -> websocket.WebSocketData:
    ws = websocket.WebSocketData()

    if messages:
        ws.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203),
            websocket.WebSocketMessage(Opcode.TEXT, True, b"hello text", 946681204),
            websocket.WebSocketMessage(Opcode.TEXT, False, b"it's me", 946681205),
        ]
    ws.close_reason = "Close Reason"
    ws.close_code = 1000
    ws.closed_by_client = False
    ws.timestamp_end = 946681205

    return ws


def tflows() -> list[flow.Flow]:
    return [
        tflow(resp=True),
        tflow(err=True),
        tflow(ws=True),
        ttcpflow(),
        ttcpflow(err=True),
        tudpflow(),
        tudpflow(err=True),
        tdnsflow(resp=True),
        tdnsflow(err=True),
    ]
