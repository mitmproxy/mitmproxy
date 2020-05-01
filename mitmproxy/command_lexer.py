import ast
import re

import pyparsing

# TODO: There is a lot of work to be done here.
# The current implementation is written in a way that _any_ input is valid,
# which does not make sense once things get more complex.

PartialQuotedString = pyparsing.Regex(
    re.compile(
        r'''
            (["'])  # start quote
            (?:
                (?:\\.)  # escape sequence
                |
                (?!\1).  # unescaped character that is not our quote nor the begin of an escape sequence. We can't use \1 in []
            )*
            (?:\1|$)  # end quote
        ''',
        re.VERBOSE
    )
)

expr = pyparsing.ZeroOrMore(
    PartialQuotedString
    | pyparsing.Word(" \r\n\t")
    | pyparsing.CharsNotIn("""'" \r\n\t""")
).leaveWhitespace()


def quote(val: str) -> str:
    if val and all(char not in val for char in "'\" \r\n\t"):
        return val
    return repr(val)  # TODO: More of a hack.


def unquote(x: str) -> str:
    quoted = (
            (x.startswith('"') and x.endswith('"'))
            or
            (x.startswith("'") and x.endswith("'"))
    )
    if quoted:
        try:
            x = ast.literal_eval(x)
        except Exception:
            x = x[1:-1]
    return x
