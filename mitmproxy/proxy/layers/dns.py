from dataclasses import dataclass
import struct

from mitmproxy import dns, flow
from mitmproxy import connection
from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.utils import expect


@dataclass
class DnsRequestHook(commands.StartHook):
    """
    A DNS query has been received.
    """

    flow: dns.DNSFlow


@dataclass
class DnsResponseHook(commands.StartHook):
    """
    A DNS response has been received or set.
    """

    flow: dns.DNSFlow


@dataclass
class DnsErrorHook(commands.StartHook):
    """
    A DNS error has occurred.
    """

    flow: dns.DNSFlow


class DNSLayer(layer.Layer):
    """
    Layer that handles resolving DNS queries.
    """

    flow: dns.DNSFlow

    def __init__(self, context: Context):
        super().__init__(context)
        self.flow = dns.DNSFlow(self.context.client, self.context.server, live=True)

    def handle_request(self, msg: dns.Message) -> layer.CommandGenerator[None]:
        self.flow.request = msg  # if already set, continue and query upstream again
        yield DnsRequestHook(
            self.flow
        )  # give hooks a chance to change the request or produce a response
        if self.flow.response:
            yield from self.handle_response(self.flow.response)
        elif not self.flow.server_conn.address:
            yield from self.handle_error("No hook has set a response.")
        else:
            if (
                self.flow.server_conn.state is connection.ConnectionState.CLOSED
            ):  # we need an upstream connection
                err = yield commands.OpenConnection(self.flow.server_conn)
                if err:
                    yield from self.handle_error(str(err))
                    return  # cannot recover from this
            yield commands.SendData(self.flow.server_conn, self.flow.request.packed)

    def handle_response(self, msg: dns.Message) -> layer.CommandGenerator[None]:
        self.flow.response = msg
        yield DnsResponseHook(self.flow)
        if self.flow.response:  # allows the response hook to suppress an answer
            yield commands.SendData(self.context.client, self.flow.response.packed)

    def handle_error(self, err: str) -> layer.CommandGenerator[None]:
        self.flow.error = flow.Error(err)
        yield DnsErrorHook(self.flow)

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        self._handle_event = self.state_query
        yield from ()

    @expect(events.DataReceived, events.ConnectionClosed)
    def state_query(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert isinstance(event, events.ConnectionEvent)
        from_client = event.connection is self.context.client

        if isinstance(event, events.DataReceived):
            try:
                msg = dns.Message.unpack(event.data)
            except struct.error as e:
                yield commands.Log(f"{event.connection} sent an invalid message: {e}")
            else:
                if from_client:
                    yield from self.handle_request(msg)
                else:
                    yield from self.handle_response(msg)

        elif isinstance(event, events.ConnectionClosed):
            other_conn = self.flow.server_conn if from_client else self.context.client
            if other_conn.state is not connection.ConnectionState.CLOSED:
                yield commands.CloseConnection(other_conn)
            self._handle_event = self.state_done
            self.flow.live = False

        else:
            raise AssertionError(f"Unexpected event: {event}")

    @expect(events.DataReceived, events.ConnectionClosed)
    def state_done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    _handle_event = state_start
