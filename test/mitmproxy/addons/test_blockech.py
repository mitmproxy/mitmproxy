from mitmproxy import dns
from mitmproxy.addons import blockech
from mitmproxy.net.dns import types
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestBlockECH:
    def test_simple(self):
        be = blockech.BlockECH()
        with taddons.context(be) as tctx:
            answers = [
                dns.ResourceRecord(
                    "dns.google",
                    dns.types.HTTPS,
                    dns.classes.IN,
                    32,
                    b"\x08\x08\x08\x08",
                ),
                dns.ResourceRecord(
                    "dns.google", dns.types.A, dns.classes.IN, 32, b"\x08\x08\x04\x04"
                ),
            ]
            resp = tutils.tdnsresp(answers=answers)
            f = tflow.tdnsflow(resp=resp)

            tctx.configure(be, blockech=False)
            be.dns_response(f)
            assert len(f.response.answers) == 2

            tctx.configure(be, blockech=True)
            be.dns_response(f)
            assert not any(answer.type == types.HTTPS for answer in f.response.answers)
