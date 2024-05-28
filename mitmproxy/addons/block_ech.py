from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy.net.dns import types


class BlockECH:
    def load(self, loader):
        loader.add_option(
            "block_ech",
            bool,
            True,
            "Strip DNS HTTPS records to prevent clients from sending Encrypted ClientHello (ECH) messages",
        )

    def dns_response(self, flow: dns.DNSFlow):
        # TODO: parse HTTPS records and remove ech value alone. For now,
        # if HTTPS record is part of response, remove that record.
        assert flow.response
        if ctx.options.block_ech:
            flow.response.answers = [
                answer for answer in flow.response.answers if answer.type != types.HTTPS
            ]
