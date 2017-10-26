import typing
from unittest import mock
from warnings import warn

import h11
from mitmproxy.net import http
from mitmproxy.net import websockets
from mitmproxy.proxy2 import events, commands
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.layers import websocket
from mitmproxy.proxy2.utils import expect


class HTTPLayer(Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: Context = None

    # this is like a mini state machine.
    state: typing.Callable[[events.Event], commands.TCommandGenerator]

    def __init__(self, context: Context):
        super().__init__(context)
        self.state = self.read_request_headers
        self.flow = mock.Mock()
        self.client_conn = h11.Connection(h11.SERVER)
        self.server_conn = h11.Connection(h11.CLIENT)

        # poor man's logging
        def log_event(orig):
            def next_event():
                e = orig()
                yield commands.Log(str(e))
                return e

            return next_event

        self.client_conn.next_event = log_event(self.client_conn.next_event)
        self.server_conn.next_event = log_event(self.server_conn.next_event)

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

            self.flow.request.headers = http.Headers(event.headers)
            self.flow_events[0].append(event)
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
            self.flow.response.headers = http.Headers(event.headers)
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
