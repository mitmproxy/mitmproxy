from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy.net.dns import types


class BlockECH:
    def load(self, loader):
        loader.add_option(
            "blockech",
            bool,
            True,
            "Prevent encrypted SNI by blocking ECH key from passing through by removing HTTPS records from answers",
        )

    def dns_response(self, flow: dns.DNSFlow):
        # TODO: parse HTTPS records and remove ech value alone. For now,
        # if HTTPS record is part of response, remove that record.
        if ctx.options.blockech:
            for answer in flow.response.answers:
                if answer.type == types.HTTPS:
                    flow.response.answers.remove(answer)
