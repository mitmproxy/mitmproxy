from mitmproxy.net.dns import response_codes


def test_to_str():
    assert response_codes.to_str(response_codes.NOERROR) == "NOERROR"
    assert response_codes.to_str(100) == "RCODE(100)"


def test_from_str():
    assert response_codes.from_str("NOERROR") == response_codes.NOERROR
    assert response_codes.from_str("RCODE(100)") == 100


def test_http_equiv_status_code():
    assert response_codes.http_equiv_status_code(response_codes.NOERROR) == 200
