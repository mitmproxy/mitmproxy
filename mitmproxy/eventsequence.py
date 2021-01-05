from typing import Iterator, Any, Dict, Type, Callable

from mitmproxy import controller
from mitmproxy import hooks
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import websocket
from mitmproxy.proxy import layers

TEventGenerator = Iterator[hooks.Hook]


def _iterate_http(f: http.HTTPFlow) -> TEventGenerator:
    if f.request:
        yield layers.http.HttpRequestHeadersHook(f)
        yield layers.http.HttpRequestHook(f)
    if f.response:
        yield layers.http.HttpResponseHeadersHook(f)
        yield layers.http.HttpResponseHook(f)
    if f.error:
        yield layers.http.HttpErrorHook(f)


def _iterate_websocket(f: websocket.WebSocketFlow) -> TEventGenerator:
    messages = f.messages
    f.messages = []
    f.reply = controller.DummyReply()
    yield layers.websocket.WebsocketStartHook(f)
    while messages:
        f.messages.append(messages.pop(0))
        yield layers.websocket.WebsocketMessageHook(f)
    if f.error:
        yield layers.websocket.WebsocketErrorHook(f)
    else:
        yield layers.websocket.WebsocketEndHook(f)


def _iterate_tcp(f: tcp.TCPFlow) -> TEventGenerator:
    messages = f.messages
    f.messages = []
    f.reply = controller.DummyReply()
    yield layers.tcp.TcpStartHook(f)
    while messages:
        f.messages.append(messages.pop(0))
        yield layers.tcp.TcpMessageHook(f)
    if f.error:
        yield layers.tcp.TcpErrorHook(f)
    else:
        yield layers.tcp.TcpEndHook(f)


_iterate_map: Dict[Type[flow.Flow], Callable[[Any], TEventGenerator]] = {
    http.HTTPFlow: _iterate_http,
    websocket.WebSocketFlow: _iterate_websocket,
    tcp.TCPFlow: _iterate_tcp,
}


def iterate(f: flow.Flow) -> TEventGenerator:
    try:
        e = _iterate_map[type(f)]
    except KeyError as err:
        raise TypeError(f"Unknown flow type: {f.__class__.__name__}") from err
    else:
        yield from e(f)
