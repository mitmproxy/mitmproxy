import re

import pyparsing

# TODO: There is a lot of work to be done here.
# The current implementation is written in a way that _any_ input is valid,
# which does not make sense once things get more complex.

PartialQuotedString = pyparsing.Regex(
    re.compile(
        r"""
            "[^"]*(?:"|$)  # double-quoted string that ends with double quote or EOF
            |
            '[^']*(?:'|$)  # single-quoted string that ends with double quote or EOF
        """,
        re.VERBOSE,
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
    if '"' not in val:
        return f'"{val}"'
    if "'" not in val:
        return f"'{val}'"
    return '"' + val.replace('"', r"\x22") + '"'


def unquote(x: str) -> str:
    if len(x) > 1 and x[0] in "'\"" and x[0] == x[-1]:
        return x[1:-1]
    else:
        return x
