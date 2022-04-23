from mitmproxy.net.dns import response_codes


def test_simple():
    assert response_codes.NOERROR == 0
    assert response_codes.to_str(response_codes.NOERROR) == "NOERROR"
    assert response_codes.to_str(100) == "RCODE(100)"
    assert response_codes.http_equiv_status_code(response_codes.NOERROR) == 200
