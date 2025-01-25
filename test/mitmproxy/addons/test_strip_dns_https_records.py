from mitmproxy import dns
from mitmproxy.addons import strip_dns_https_records
from mitmproxy.net.dns import https_records
from mitmproxy.net.dns import types
from mitmproxy.net.dns.https_records import SVCParamKeys
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestStripECH:
    def test_strip_ech(self):
        se = strip_dns_https_records.StripDnsHttpsRecords()
        with taddons.context(se) as tctx:
            params1 = {
                SVCParamKeys.PORT.value: b"\x01\xbb",
                SVCParamKeys.ECH.value: b"testbytes",
            }
            params2 = {SVCParamKeys.PORT.value: b"\x01\xbb"}
            record1 = https_records.HTTPSRecord(1, "example.com", params1)
            record2 = https_records.HTTPSRecord(1, "example.com", params2)
            answers = [
                dns.ResourceRecord(
                    "dns.google",
                    dns.types.A,
                    dns.classes.IN,
                    32,
                    b"\x08\x08\x08\x08",
                ),
                dns.ResourceRecord(
                    "dns.google",
                    dns.types.HTTPS,
                    dns.classes.IN,
                    32,
                    https_records.pack(record1),
                ),
                dns.ResourceRecord(
                    "dns.google",
                    dns.types.HTTPS,
                    dns.classes.IN,
                    32,
                    https_records.pack(record2),
                ),
            ]
            resp = tutils.tdnsresp(answers=answers)
            f = tflow.tdnsflow(resp=resp)
            tctx.configure(se, strip_ech=True)
            se.dns_response(f)
            assert all(
                answer.https_ech is None
                for answer in f.response.answers
                if answer.type == types.HTTPS
            )

    def test_strip_alpn(self):
        se = strip_dns_https_records.StripDnsHttpsRecords()
        with taddons.context(se) as tctx:
            record2 = https_records.HTTPSRecord(
                1,
                "example.com",
                {
                    SVCParamKeys.ALPN.value: b"\x02h2\x02h3",
                },
            )
            answers = [
                dns.ResourceRecord(
                    "dns.google",
                    dns.types.HTTPS,
                    dns.classes.IN,
                    32,
                    https_records.pack(record2),
                )
            ]
            f = tflow.tdnsflow(resp=tutils.tdnsresp(answers=answers))

            se.dns_response(f)
            assert f.response.answers[0].https_alpn == (b"h2", b"h3")

            tctx.configure(se, http3=False)
            se.dns_response(f)
            assert f.response.answers[0].https_alpn == (b"h2",)

            f.response.answers[0].https_alpn = [b"h3"]
            se.dns_response(f)
            assert f.response.answers[0].https_alpn is None
