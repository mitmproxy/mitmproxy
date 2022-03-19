from dataclasses import dataclass
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


class DNSLayer(layer.Layer):
    """
    Layer that handles resolving DNS queries.
    """
    flow: dns.DNSFlow

    def __init__(self, context: Context):
        super().__init__(context)
        self.flow = dns.DNSFlow(self.context.client, self.context.server, True)

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:
        pass

    _handle_event = start
