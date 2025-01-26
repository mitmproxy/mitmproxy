from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy.net.dns import types


class StripDnsHttpsRecords:
    def load(self, loader):
        loader.add_option(
            "strip_ech",
            bool,
            True,
            "Strip Encrypted ClientHello (ECH) data from DNS HTTPS records so that mitmproxy can generate matching certificates.",
        )

    def dns_response(self, flow: dns.DNSFlow):
        assert flow.response
        if ctx.options.strip_ech:
            for answer in flow.response.answers:
                if answer.type == types.HTTPS:
                    answer.https_ech = None
        if not ctx.options.http3:
            for answer in flow.response.answers:
                if (
                    answer.type == types.HTTPS
                    and answer.https_alpn is not None
                    and any(
                        # HTTP/3 or any of the spec drafts (h3-...)?
                        a == b"h3" or a.startswith(b"h3-")
                        for a in answer.https_alpn
                    )
                ):
                    alpns = tuple(
                        a
                        for a in answer.https_alpn
                        if a != b"h3" and not a.startswith(b"h3-")
                    )
                    answer.https_alpn = alpns or None
