from unittest.mock import MagicMock
from unittest.mock import patch

import pyparsing as pp

from mitmproxy.utils import pyparsing_utils


def test_pyparsing_utils():
    # 1. Test with the real element in the current environment
    element = pp.Literal("foo")
    pyparsing_utils.set_parse_action(element, lambda x: x)
    pyparsing_utils.leave_whitespace(element)
    pyparsing_utils.parse_string(element, "foo")
    pyparsing_utils.infix_notation(element, [])
    pyparsing_utils.QuotedString("'", esc_char="\\")
    pyparsing_utils.QuotedString("'")

    # 2. Mock PP_MAJOR to 3 and use a mock element to cover that branch without AttributeError
    with patch("mitmproxy.utils.pyparsing_utils.PP_MAJOR", 3):
        mock_element = MagicMock()
        pyparsing_utils.set_parse_action(mock_element, lambda x: x)
        mock_element.set_parse_action.assert_called_once()

        pyparsing_utils.leave_whitespace(mock_element)
        mock_element.leave_whitespace.assert_called_once()

        pyparsing_utils.parse_string(mock_element, "foo")
        mock_element.parse_string.assert_called_once_with("foo", parse_all=False)

        with patch("pyparsing.infix_notation", create=True) as m:
            pyparsing_utils.infix_notation(mock_element, [])
            m.assert_called_once()

        with patch("pyparsing.QuotedString", create=True) as m:
            pyparsing_utils.QuotedString("'", esc_char="\\")
            m.assert_called_with("'", esc_char="\\")

    # 3. Mock PP_MAJOR to 2 and use a mock element to cover that branch
    with patch("mitmproxy.utils.pyparsing_utils.PP_MAJOR", 2):
        mock_element = MagicMock()
        pyparsing_utils.set_parse_action(mock_element, lambda x: x)
        mock_element.setParseAction.assert_called_once()

        pyparsing_utils.leave_whitespace(mock_element)
        mock_element.leaveWhitespace.assert_called_once()

        pyparsing_utils.parse_string(mock_element, "foo")
        mock_element.parseString.assert_called_once_with("foo", parseAll=False)

        with patch("pyparsing.infixNotation", create=True) as m:
            pyparsing_utils.infix_notation(mock_element, [])
            m.assert_called_once()

        with patch("pyparsing.QuotedString", create=True) as m:
            pyparsing_utils.QuotedString("'", esc_char="\\")
            m.assert_called_with("'", escChar="\\")
