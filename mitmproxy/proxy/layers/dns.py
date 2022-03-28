from dataclasses import dataclass
import enum
import struct
from typing import Dict

from mitmproxy import dns, flow as mflow
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


class DnsMode(enum.Enum):
    Simple = "simple"
    Forward = "forward"
    Transparent = "transparent"


class DNSLayer(layer.Layer):
    """
    Layer that handles resolving DNS queries.
    """

    flows: Dict[int, dns.DNSFlow]
    mode: DnsMode

    def __init__(self, context: Context, mode: DnsMode):
        super().__init__(context)
        self.flows = dict()
        self.mode = mode

    def handle_request(self, flow: dns.DNSFlow) -> layer.CommandGenerator[None]:
        orig_id = flow.request.id
        yield DnsRequestHook(flow)  # give hooks a chance to change the request or produce a response
        if orig_id != flow.request.id:  # handle the case of a hook changing the request id
            del self.flows[orig_id]
            self.flows[flow.request.id] = flow
        if flow.response:
            yield from self.handle_response(flow)
        elif self.mode is DnsMode.Simple:
            yield from self.handle_error(flow, "Simple hook has not set a response.")
        else:
            if flow.server_conn.state is connection.ConnectionState.CLOSED:  # we need an upstream connection
                err = yield commands.OpenConnection(flow.server_conn)
                if err:
                    yield from self.handle_error(flow, str(err))
                    return  # cannot recover from this
            yield commands.SendData(flow.server_conn, flow.request.packed)

    def handle_response(self, flow: dns.DNSFlow) -> layer.CommandGenerator[None]:
        yield DnsResponseHook(flow)
        if flow.response:  # allows the response hook to suppress an answer
            yield commands.SendData(self.context.client, flow.response.packed)
        self.remove_flow(flow)

    def handle_error(self, flow: dns.DNSFlow, err: str) -> layer.CommandGenerator[None]:
        flow.error = mflow.Error(err)
        yield DnsErrorHook(flow)
        self.remove_flow(flow)

    def remove_flow(self, flow: dns.DNSFlow) -> None:
        del self.flows[flow.request.id]
        flow.live = False

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:
        self._handle_event = self.query
        yield from ()

    @expect(events.DataReceived, events.ConnectionClosed)
    def query(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert isinstance(event, events.ConnectionEvent)
        from_client = event.connection is self.context.client

        if isinstance(event, events.DataReceived):
            try:
                msg = dns.Message.unpack(event.data)
            except struct.error as e:
                yield commands.Log(f"{event.connection} sent an invalid message: {e}")
            else:
                if msg.id in self.flows:
                    flow = self.flows[msg.id]
                    if from_client:
                        flow.request = msg  # override the request and handle it again
                        yield from self.handle_request(flow)
                    else:
                        flow.response = msg
                        yield from self.handle_response(flow)
                else:
                    if from_client:
                        flow = dns.DNSFlow(self.context.client, self.context.server)
                        flow.request = msg
                        self.flows[msg.id] = flow
                        yield from self.handle_request(flow)
                    else:
                        yield commands.Log(f"{event.connection} responded to unknown message #{msg.id}")

        elif isinstance(event, events.ConnectionClosed):
            other_conn = self.context.server if from_client else self.context.client
            if other_conn.state is not connection.ConnectionState.CLOSED:
                yield commands.CloseConnection(other_conn)
            self._handle_event = self.done
            flows = self.flows.values()
            while flows:
                self.remove_flow(next(iter(flows)))

        else:
            raise AssertionError(f"Unexpected event: {event}")

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    _handle_event = start
