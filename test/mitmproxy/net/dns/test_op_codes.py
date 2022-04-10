from mitmproxy.net.dns import op_codes


def test_simple():
    assert op_codes.QUERY == 0
    assert op_codes.str(op_codes.QUERY) == "QUERY"
    assert op_codes.str(100) == "OPCODE(100)"
