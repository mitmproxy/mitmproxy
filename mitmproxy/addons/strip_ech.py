from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy.net.dns import types


class StripECH:
    def load(self, loader):
        loader.add_option(
            "strip_ech",
            bool,
            True,
            "Strip DNS HTTPS records to prevent clients from sending Encrypted ClientHello (ECH) messages",
        )

    def dns_response(self, flow: dns.DNSFlow):
        assert flow.response
        if ctx.options.strip_ech:
            for answer in flow.response.answers:
                if answer.type == types.HTTPS:
                    answer.https_ech = None
