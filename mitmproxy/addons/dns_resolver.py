from mitmproxy import ctx, dns


class DnsResolver:
    async def dns_request(self, flow: dns.DNSFlow) -> None:
        # handle regular mode requests here to not block the layer
        if ctx.options.dns_mode == "regular":
            flow.response = await flow.request.resolve()
