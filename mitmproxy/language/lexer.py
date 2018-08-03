import re
import typing

import ply.lex as lex


class CommandLanguageLexer:
    tokens = (
        "WHITESPACE",
        "PIPE",
        "LPAREN", "RPAREN",
        "LBRACE", "RBRACE",
        "PLAIN_STR", "QUOTED_STR",
        "COMMAND"
    )
    states = (
        ("interactive", "inclusive"),
    )

    def __init__(self, oneword_commands: typing.Sequence[str]) -> None:
        self.oneword_commands = dict.fromkeys(oneword_commands, "COMMAND")

    # Main(INITIAL) state
    t_ignore_WHITESPACE = r"\s+"
    t_PIPE = r"\|"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACE = r"\["
    t_RBRACE = r"\]"

    special_symbols = re.escape("()[]|")
    plain_str = rf"[^{special_symbols}\s]+"

    def t_COMMAND(self, t):
        r"""\w+(\.\w+)+"""
        return t

    def t_QUOTED_STR(self, t):
        r"""
            \'+[^\']*\'+ |  # Single-quoted string
            \"+[^\"]*\"+    # Double-quoted string
        """
        return t

    @lex.TOKEN(plain_str)
    def t_PLAIN_STR(self, t):
        t.type = self.oneword_commands.get(t.value, "PLAIN_STR")
        return t

    # Interactive state
    t_interactive_WHITESPACE = r"\s+"

    def build(self, **kwargs):
        self.lexer = lex.lex(module=self,
                             errorlog=lex.NullLogger(), **kwargs)


def create_lexer(cmdstr: str, oneword_commands: typing.Sequence[str]) -> lex.Lexer:
    command_lexer = CommandLanguageLexer(oneword_commands)
    command_lexer.build()
    command_lexer.lexer.input(cmdstr)
    return command_lexer.lexer


def get_tokens(cmdstr: str, state="interactive",
               oneword_commands=None) -> typing.List[lex.LexToken]:
    if oneword_commands is None:
        oneword_commands = []
    lexer = create_lexer(cmdstr, oneword_commands)
    # Switching to the other state
    lexer.begin(state)
    return list(lexer)
