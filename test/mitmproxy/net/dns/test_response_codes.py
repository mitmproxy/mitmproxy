from mitmproxy.net.dns import response_codes


def test_simple():
    assert response_codes.NOERROR == 0
    assert response_codes.str(response_codes.NOERROR) == "NOERROR"
    assert response_codes.str(100) == "RCODE(100)"
