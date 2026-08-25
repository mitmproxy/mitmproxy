from mitmproxy.net.dns import op_codes


def test_to_str():
    assert op_codes.to_str(op_codes.QUERY) == "QUERY"
    assert op_codes.to_str(100) == "OPCODE(100)"


def test_from_str():
    assert op_codes.from_str("QUERY") == op_codes.QUERY
    assert op_codes.from_str("OPCODE(100)") == 100
