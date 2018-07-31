import time
from typing import Dict, List  # noqa

import h11
from mitmproxy import http
from mitmproxy.net.http import Headers
from mitmproxy.proxy2 import events, commands
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.layers.http import _make_event_from_request
from mitmproxy.proxy2.utils import expect


class ServerHTTP1Layer(Layer):
    flow: http.HTTPFlow = None

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        if not self.context.server.connected:
            # TODO: Can be done later
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.Log(f"Cannot open connection: {err}", level="error")
                # FIXME: Handle properly.

        self.h11 = h11.Connection(h11.CLIENT)

        # debug
        # \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/ \/
        def log_event(orig):
            def next_event():
                e = orig()
                if True:
                    yield commands.Log(f"[h11] {e}")
                return e

            return next_event

        self.h11.next_event = log_event(self.h11.next_event)
        # /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\ /\
        self.child_layer = HTTPLayer(self.context)
        self.event_to_child(events.Start())

        yield commands.Log("HTTP/1 connection started")

        self._handle_event = self._handle

    _handle_event = start

    def event_to_child(self, event: events.Event):
        for command in self.child_layer.handle_event(event):
            if isinstance(command, HttpCommand):
                yield from self.handle_http_command(command)
            else:
                yield command

    def handle_http_command(self, command: HttpCommand):
        bytes_to_send = None
        if isinstance(command, SendRequestHeaders):
            self.flow = command.flow
            self.flow.request.http_version = b"HTTP/1.1"
            h11_event = _make_event_from_request(self.flow.request)
            bytes_to_send = self.h11.send(h11_event)

        elif isinstance(command, SendRequestComplete):
            bytes_to_send = self.h11.send(h11.EndOfMessage())
        elif isinstance(command, SendRequestData):
            yield commands.Log(f"Server HTTP1Layer unimplemented HttpCommand: {command}",
                               level="error")
        else:
            yield command
        if bytes_to_send:
            yield commands.SendData(self.context.server, bytes_to_send)

    def _handle(self, event: events.Event):
        if isinstance(event, HttpEvent):
            yield from self.event_to_child(event)
        elif isinstance(event, events.DataReceived):
            self.h11.receive_data(event.data)

            while True:
                h11_event = yield from self.h11.next_event()
                if h11_event is h11.NEED_DATA:
                    break
                elif isinstance(h11_event, h11.Response):
                    yield commands.Log(f"h11 responseheaders: {h11_event}")
                    self.flow.response = http.HTTPResponse(
                        b"HTTP/1.1",
                        h11_event.status_code,
                        h11_event.reason,
                        h11_event.headers,
                        None,
                        time.time()
                    )
                    yield from self.event_to_child(ResponseHeaders(self.flow))
                elif isinstance(h11_event, h11.Data):
                    yield from self.event_to_child(ResponseData(self.flow, h11_event.data))
                elif isinstance(h11_event, h11.EndOfMessage):
                    yield from self.event_to_child(ResponseComplete(self.flow))
                else:
                    raise NotImplementedError(h11_event)
        else:
            yield from self.event_to_child(event)


class ClientHTTP1Layer(Layer):
    flow: http.HTTPFlow = None

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        raise NotImplemented
