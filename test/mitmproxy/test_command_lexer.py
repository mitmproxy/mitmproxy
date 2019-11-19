import pyparsing
import pytest

from mitmproxy import command_lexer


@pytest.mark.parametrize(
    "test_input,valid", [
        ("'foo'", True),
        ('"foo"', True),
        ("'foo' bar'", False),
        ("'foo\\' bar'", True),
        ("'foo' 'bar'", False),
        ("'foo'x", False),
        ('''"foo    ''', True),
        ('''"foo 'bar'   ''', True),
    ]
)
def test_partial_quoted_string(test_input, valid):
    if valid:
        assert command_lexer.PartialQuotedString.parseString(test_input, parseAll=True)[0] == test_input
    else:
        with pytest.raises(pyparsing.ParseException):
            command_lexer.PartialQuotedString.parseString(test_input, parseAll=True)


@pytest.mark.parametrize(
    "test_input,expected", [
        ("'foo'", ["'foo'"]),
        ('"foo"', ['"foo"']),
        ("'foo' 'bar'", ["'foo'", ' ', "'bar'"]),
        ("'foo'x", ["'foo'", 'x']),
        ('''"foo''', ['"foo']),
        ('''"foo 'bar' ''', ['''"foo 'bar' ''']),
    ]
)
def test_expr(test_input, expected):
    assert list(command_lexer.expr.parseString(test_input, parseAll=True)) == expected
