from . import full_eval
from mitmproxy.contentviews import dns

DNS_HTTPS_RECORD_RESPONSE = bytes.fromhex(
    "00008180000100010000000107746c732d656368036465760000410001c00c004100010000003c00520001000005004b0049fe0d00"
    "452b00200020015881d41a3e2ef8f2208185dc479245d20624ddd0918a8056f2e26af47e2628000800010001000100034012707562"
    "6c69632e746c732d6563682e646576000000002904d0000000000000"
)


def test_simple():
    v = full_eval(dns.ViewDns())
    assert v(DNS_HTTPS_RECORD_RESPONSE)
    assert not v(b"foobar")


def test_render_priority():
    v = dns.ViewDns()
    assert v.render_priority(b"", content_type="application/dns-message")
    assert not v.render_priority(b"", content_type="text/plain")
    assert not v.render_priority(b"")
