from mitmproxy import controller
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import websocket

Events = frozenset([
    "clientconnect",
    "clientdisconnect",
    "serverconnect",
    "serverdisconnect",

    "tcp_start",
    "tcp_message",
    "tcp_error",
    "tcp_end",

    "http_connect",
    "request",
    "requestheaders",
    "response",
    "responseheaders",
    "error",

    "websocket_handshake",
    "websocket_start",
    "websocket_message",
    "websocket_error",
    "websocket_end",

    "next_layer",

    "configure",
    "done",
    "log",
    "start",
    "tick",
])


def event_sequence(f):
    if isinstance(f, http.HTTPFlow):
        if f.request:
            yield "requestheaders", f
            yield "request", f
        if f.response:
            yield "responseheaders", f
            yield "response", f
        if f.error:
            yield "error", f
    elif isinstance(f, websocket.WebSocketFlow):
        messages = f.messages
        f.messages = []
        f.reply = controller.DummyReply()
        yield "websocket_start", f
        while messages:
            f.messages.append(messages.pop(0))
            yield "websocket_message", f
        if f.error:
            yield "websocket_error", f
        yield "websocket_end", f
    elif isinstance(f, tcp.TCPFlow):
        messages = f.messages
        f.messages = []
        f.reply = controller.DummyReply()
        yield "tcp_start", f
        while messages:
            f.messages.append(messages.pop(0))
            yield "tcp_message", f
        if f.error:
            yield "tcp_error", f
        yield "tcp_end", f
    else:
        raise NotImplementedError
