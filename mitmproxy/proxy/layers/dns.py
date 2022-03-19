from dataclasses import dataclass
import enum
import struct
from typing import Dict

from mitmproxy import dns
from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.utils import expect


@dataclass
class DnsRequestHook(commands.StartHook):
    """
    A DNS query has been received.
    """

    name = "resolve"
    flow: dns.DNSFlow


@dataclass
class DnsResponseHook(commands.StartHook):
    """
    A DNS response has been received or set.
    """

    name = "resolved"
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

    def __init__(self, context: Context):
        super().__init__(context)
        self.flow = dict()

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:
        self.context.options.dns_mode
        pass

    @expect(events.DataReceived, events.ConnectionClosed)
    def query(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert isinstance(event, events.ConnectionEvent)

        if isinstance(event, events.DataReceived):
            from_client = event.connection == self.context.client
            try:
                msg = dns.Message.unpack(event.data)
            except struct.error as e:
                flow = dns.DNSFlow(self.context.client, self.context.server if from_client else event.connection, True)
                flow.error = str(e)
                yield DnsErrorHook(flow)
                return
            if msg.id in self.flows:
                pass
            else:
                if from_client:
                    if self.mode is DnsMode.Simple:
                        flow = dns.DNSFlow(self.context.client, self.context.server, True)
                        flow.request = msg
                        yield DnsRequestHook(flow)
                        if not flow.response:
                            if not msg.query:
                                flow.error = "Received non-query DNS message from client."
                                yield DnsErrorHook(flow)
                                return
                            if msg.op_code is not dns.OpCode.QUERY:
                                flow.response = msg.fail(dns.ResponseCode.NOTIMP)
                            else:
                                answers = []
                                for question in msg.questions:
                                    pass
                                flow.response = msg.succeed(answers)
                        self.flows[msg.id] = flow
                        yield DnsResponseHook(flow)
                        yield commands.SendData(self.context.client, flow.response.packed)
                    elif self.mode is DnsMode.Forward:
                        pass
                    elif self.mode is DnsMode.Transparent:
                        pass
                    else:
                        raise AssertionError(f"Unknown DNS mode: {self.mode}")
                else:
                    flow = dns.DNSFlow(self.context.client, self.context.server, True)
                    flow.response = msg
                    flow.error = f"Received response for unknown id {msg.id}."
                    yield DnsErrorHook(flow)

    _handle_event = start
