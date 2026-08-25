"""
Spoof DNS responses.

In this example, we fiddle with IPv6 (AAAA) records:
 - For example.com, `::1` is returned.
   (domain is hosted on localhost)
 - For example.org, an NXDOMAIN error is returned.
   (domain does not exist)
 - For all other domains, return a non-error response without any records.
   (domain exists, but has no IPv6 configured)
"""

import ipaddress
import logging

from mitmproxy import dns


def dns_request(flow: dns.DNSFlow) -> None:
    q = flow.request.question
    if q and q.type == dns.types.AAAA:
        logging.info(f"Spoofing IPv6 records for {q.name}...")
        if q.name == "example.com":
            flow.response = flow.request.succeed(
                [
                    dns.ResourceRecord(
                        name="example.com",
                        type=dns.types.AAAA,
                        class_=dns.classes.IN,
                        ttl=dns.ResourceRecord.DEFAULT_TTL,
                        data=ipaddress.ip_address("::1").packed,
                    )
                ]
            )
        elif q.name == "example.org":
            flow.response = flow.request.fail(dns.response_codes.NXDOMAIN)
        else:
            flow.response = flow.request.succeed([])
