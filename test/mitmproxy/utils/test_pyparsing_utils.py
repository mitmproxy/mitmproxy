from mitmproxy.utils import pyparsing_utils


def test_pyparsing_utils():
    # Simple test to ensure the module is importable and has the expected functions
    assert hasattr(pyparsing_utils, "set_parse_action")
    assert hasattr(pyparsing_utils, "leave_whitespace")
    assert hasattr(pyparsing_utils, "parse_string")
    assert hasattr(pyparsing_utils, "infix_notation")
    assert hasattr(pyparsing_utils, "QuotedString")
