import struct
from dataclasses import dataclass

from mitmproxy import dns
from mitmproxy import flow as mflow
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
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

    flows: dict[int, dns.DNSFlow]

    def __init__(self, context: Context):
        super().__init__(context)
        self.flows = {}

    def handle_request(
        self, flow: dns.DNSFlow, msg: dns.Message
    ) -> layer.CommandGenerator[None]:
        flow.request = msg  # if already set, continue and query upstream again
        yield DnsRequestHook(flow)
        if flow.response:
            yield from self.handle_response(flow, flow.response)
        elif not self.context.server.address:
            yield from self.handle_error(
                flow, "No hook has set a response and there is no upstream server."
            )
        else:
            if not self.context.server.connected:
                err = yield commands.OpenConnection(self.context.server)
                if err:
                    yield from self.handle_error(flow, str(err))
                    # cannot recover from this
                    return
            yield commands.SendData(self.context.server, flow.request.packed)

    def handle_response(
        self, flow: dns.DNSFlow, msg: dns.Message
    ) -> layer.CommandGenerator[None]:
        flow.response = msg
        yield DnsResponseHook(flow)
        if flow.response:
            yield commands.SendData(self.context.client, flow.response.packed)

    def handle_error(self, flow: dns.DNSFlow, err: str) -> layer.CommandGenerator[None]:
        flow.error = mflow.Error(err)
        yield DnsErrorHook(flow)

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
                yield commands.CloseConnection(event.connection)
                self._handle_event = self.state_done
            else:
                try:
                    flow = self.flows[msg.id]
                except KeyError:
                    flow = dns.DNSFlow(
                        self.context.client, self.context.server, live=True
                    )
                    self.flows[msg.id] = flow
                if from_client:
                    yield from self.handle_request(flow, msg)
                else:
                    yield from self.handle_response(flow, msg)

        elif isinstance(event, events.ConnectionClosed):
            other_conn = self.context.server if from_client else self.context.client
            if other_conn.connected:
                yield commands.CloseConnection(other_conn)
            self._handle_event = self.state_done
            for flow in self.flows.values():
                flow.live = False

        else:
            raise AssertionError(f"Unexpected event: {event}")

    @expect(events.DataReceived, events.ConnectionClosed)
    def state_done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    _handle_event = state_start
