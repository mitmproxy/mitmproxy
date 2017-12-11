import enum
import typing
from warnings import warn

import h11
from mitmproxy import http
from mitmproxy.net import http as net_http
from mitmproxy.net import websockets
from mitmproxy.net.http import url
from mitmproxy.net.http.http1.read import _parse_authority_form
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import events, commands, context
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer, NextLayer
from mitmproxy.proxy2.layers import websocket
from mitmproxy.proxy2.utils import expect


class FirstLineFormat(enum.Enum):
    authority = "authority"
    relative = "relative"
    absolute = "absolute"


MODE_REQUEST_FORMS = {
    HTTPMode.regular: (FirstLineFormat.authority, FirstLineFormat.absolute),
    HTTPMode.transparent: (FirstLineFormat.relative,),
    HTTPMode.upstream: (FirstLineFormat.authority, FirstLineFormat.absolute),
}


def _make_request_from_event(event: h11.Request) -> http.HTTPRequest:
    if event.target == b"*" or event.target.startswith(b"/"):
        form = "relative"
        path = event.target
        scheme, host, port = None, None, None
    elif event.method == b"CONNECT":
        form = "authority"
        host, port = _parse_authority_form(event.target)
        scheme, path = None, None
    else:
        form = "absolute"
        scheme, host, port, path = url.parse(event.target)

    return http.HTTPRequest(
        form,
        event.method,
        scheme,
        host,
        port,
        path,
        b"HTTP/" + event.http_version,
        event.headers,
        None,
        -1  # FIXME: first_byte_timestamp
    )


def validate_request_form(
        mode: HTTPMode,
        first_line_format: FirstLineFormat,
        scheme: str
) -> None:
    if first_line_format == FirstLineFormat.absolute and scheme != "http":
        raise ValueError(f"Invalid request scheme: {scheme}")

    allowed_request_forms = MODE_REQUEST_FORMS[mode]
    if first_line_format not in allowed_request_forms:
        if mode == HTTPMode.transparent:
            desc = "HTTP CONNECT" if first_line_format == "authority" else "absolute-form"
            raise ValueError(
                f"""
                Mitmproxy received an {desc} request even though it is not running
                in regular mode. This usually indicates a misconfiguration,
                please see the mitmproxy mode documentation for details.
                """
            )
        else:
            expected = ' or '.join(x.value for x in allowed_request_forms)
            raise ValueError(
                f"Invalid HTTP request form (expected: {expected}, got: {first_line_format})")


class HTTPLayer(Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: Context = None
    mode: HTTPMode

    # this is like a mini state machine.
    state: typing.Callable[[events.Event], commands.TCommandGenerator]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.state = self.read_request_headers
        self.flow = http.HTTPFlow(self.context.client, self.context.server)
        self.client_conn = h11.Connection(h11.SERVER)
        self.server_conn = h11.Connection(h11.CLIENT)

        # debug
        # \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/
        def log_event(orig):
            def next_event():
                e = orig()
                yield commands.Log(f"[h11] {e}")
                return e

            return next_event

        self.client_conn.next_event = log_event(self.client_conn.next_event)
        self.server_conn.next_event = log_event(self.server_conn.next_event)
        # /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\
        # this is very preliminary: [request_events, response_events]
        self.flow_events = [[], []]

    @expect(events.Start, events.DataReceived, events.ConnectionClosed)
    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.Start):
            return
        if isinstance(event, events.DataReceived):
            if event.connection == self.context.client:
                self.client_conn.receive_data(event.data)
            else:
                self.server_conn.receive_data(event.data)
        elif isinstance(event, events.ConnectionClosed):
            return warn("unimplemented: http.handle:close")

        yield from self.state()

    def read_request_headers(self):
        event = yield from self.client_conn.next_event()
        if event is h11.NEED_DATA:
            return
        elif isinstance(event, h11.Request):
            yield commands.Log(f"requestheaders: {event}")

            if self.client_conn.client_is_waiting_for_100_continue:
                raise NotImplementedError()

            self.flow.request = _make_request_from_event(event)
            validate_request_form(self.mode, FirstLineFormat(self.flow.request.first_line_format), self.flow.request.scheme)

            yield commands.Hook("requestheaders", self.flow)

            self.state = self.read_request_body
            yield from self.read_request_body()  # there may already be further events.
        else:
            raise TypeError(f"Unexpected event: {event}")

    def read_request_body(self):
        while True:
            event = yield from self.client_conn.next_event()
            if event is h11.NEED_DATA:
                return
            elif isinstance(event, h11.Data):
                self.flow_events[0].append(event)
            elif isinstance(event, h11.EndOfMessage):
                self.flow_events[0].append(event)
                yield commands.Log(f"request {self.flow_events}")

                if self.flow.request.first_line_format == FirstLineFormat.authority.value:
                    if self.mode == HTTPMode.regular:
                        yield commands.Hook("http_connect", self.flow)
                        self.context.server = context.Server(
                            (self.flow.request.host, self.flow.request.port)
                        )
                        yield commands.SendData(
                            self.context.client,
                            b'%s 200 Connection established\r\n\r\n' % self.flow.request.data.http_version
                        )
                        child_layer = NextLayer(self.context)
                        self._handle_event = child_layer.handle_event
                        yield from child_layer.handle_event(events.Start())
                        return

                    if self.mode == HTTPMode.upstream:
                        raise NotImplementedError()

                yield from self._send_request()
                return
            else:
                raise TypeError(f"Unexpected event: {event}")

    def _send_request(self):
        if not self.context.server.connected:
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.Log(f"error {err}")
                yield commands.CloseConnection(self.context.client)
                self._handle_event = self.done
                return
        for e in self.flow_events[0]:
            bytes_to_send = self.server_conn.send(e)
            yield commands.SendData(self.context.server, bytes_to_send)
        self.state = self.read_response_headers

    def read_response_headers(self):
        event = yield from self.server_conn.next_event()
        if event is h11.NEED_DATA:
            return
        elif isinstance(event, h11.Response):
            yield commands.Log(f"responseheaders {event}")

            self.flow_events[1].append(event)
            self.state = self.read_response_body
            yield from self.read_response_body()  # there may already be further events.
        elif isinstance(event, h11.InformationalResponse):
            self.flow.response.headers = net_http.Headers(event.headers)
            if event.status_code == 101 and websockets.check_handshake(self.flow.response.headers):
                child_layer = websocket.WebsocketLayer(self.context, self.flow)
                yield from child_layer.handle_event(events.Start())
                self._handle_event = child_layer.handle_event
                return
        else:
            raise TypeError(f"Unexpected event: {event}")

    def read_response_body(self):
        while True:
            event = yield from self.server_conn.next_event()
            if event is h11.NEED_DATA:
                return
            elif isinstance(event, h11.Data):
                self.flow_events[1].append(event)
            elif isinstance(event, h11.EndOfMessage):
                self.flow_events[1].append(event)
                yield commands.Log(f"response {self.flow_events}")
                yield from self._send_response()
                return
            else:
                raise TypeError(f"Unexpected event: {event}")

    def _send_response(self):
        for e in self.flow_events[1]:
            bytes_to_send = self.client_conn.send(e)
            yield commands.SendData(self.context.client, bytes_to_send)

        # reset for next request.
        self.state = self.read_request_headers
        self.flow_events = [[], []]
        self.client_conn.start_next_cycle()
        self.server_conn.start_next_cycle()

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _):
        yield from ()
