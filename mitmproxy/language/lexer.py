import re
import typing

import ply.lex as lex

from mitmproxy import exceptions


class CommandLanguageLexer:
    tokens = (
        "WHITESPACE",
        "ARRAY",
        "COMMAND",
        "PLAIN_STR",
        "QUOTED_STR"
    )

    special_symbols = re.escape(",'\"")  # Symbols to ignore in PLAIN_STR

    t_ignore_WHITESPACE = r"\s+"  # We won't ignore it in the new language
    t_ARRAY = r"\w+(\,\w+)+"
    t_PLAIN_STR = fr"[^{special_symbols}\s]+"
    t_QUOTED_STR = r""" 
    \'+[^\']*\'+ |  # Single-quoted string
    \"+[^\"]*\"+    # Double-quoted string
    """

    def __init__(self, error=True):
        self.error = error

    def t_COMMAND(self, t):
        r"""\w+(\.\w+)+"""
        return t

    def t_error(self, t):
        t.lexer.skip(1)
        if self.error:
            raise exceptions.CommandError(f"Illegal character '{t.value[0]}'")

    def build(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)


def create_lexer(cmdstr: str, error=True) -> lex.Lexer:
    command_lexer = CommandLanguageLexer(error)
    command_lexer.build()
    command_lexer.lexer.input(cmdstr)
    return command_lexer.lexer


def get_tokens(cmdstr: str) -> typing.List[str]:
    lexer = create_lexer(cmdstr, True)
    return [token.value for token in lexer]
