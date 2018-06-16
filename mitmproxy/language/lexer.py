import typing

import ply.lex as lex


class CommandLanguageLexer:
    tokens = (
        "WHITESPACE",
        "COMMAND",
        "PLAIN_STR",
        "QUOTED_STR"
    )
    states = (
        ("interactive", "inclusive"),
    )

    def __init__(self, oneword_commands: typing.Sequence[str]):
        self.oneword_commands = dict.fromkeys(oneword_commands, "COMMAND")

    # Main(INITIAL) state
    t_ignore_WHITESPACE = r"\s+"

    def t_COMMAND(self, t):
        r"""\w+(\.\w+)+"""
        return t

    def t_QUOTED_STR(self, t):
        r"""
            \'+[^\']*\'+ |  # Single-quoted string
            \"+[^\"]*\"+    # Double-quoted string
        """
        return t

    def t_PLAIN_STR(self, t):
        r"""[^\s]+"""
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


def get_tokens(cmdstr: str, state="interactive") -> typing.List[str]:
    lexer = create_lexer(cmdstr, [])
    # Switching to the other state
    lexer.begin(state)
    return [token.value for token in lexer]
