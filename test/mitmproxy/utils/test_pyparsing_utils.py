from unittest.mock import patch

import pyparsing as pp

from mitmproxy.utils import pyparsing_utils


def test_pyparsing_utils():
    element = pp.Literal("foo")

    with patch("mitmproxy.utils.pyparsing_utils.PP_MAJOR", 3):
        assert pyparsing_utils.set_parse_action(element, lambda x: x)
        assert pyparsing_utils.leave_whitespace(element)
        assert pyparsing_utils.parse_string(element, "foo")
        assert pyparsing_utils.infix_notation(element, [])
        assert pyparsing_utils.QuotedString("'", esc_char="\\")

    with patch("mitmproxy.utils.pyparsing_utils.PP_MAJOR", 2):
        assert pyparsing_utils.set_parse_action(element, lambda x: x)
        assert pyparsing_utils.leave_whitespace(element)
        assert pyparsing_utils.parse_string(element, "foo")
        assert pyparsing_utils.infix_notation(element, [])
        assert pyparsing_utils.QuotedString("'", esc_char="\\")
        assert pyparsing_utils.QuotedString("'")
