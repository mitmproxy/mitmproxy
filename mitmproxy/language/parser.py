import typing

import ply.lex as lex
import ply.yacc as yacc

import mitmproxy.command  # noqa
from mitmproxy import exceptions
from mitmproxy.language.lexer import CommandLanguageLexer


class CommandLanguageParser:
    # the list of possible tokens is always required
    tokens = CommandLanguageLexer.tokens

    def __init__(self,
                 command_manager: "mitmproxy.command.CommandManager") -> None:
        self.return_value: typing.Any = None
        self._pipe_value: typing.Any = None
        self.command_manager = command_manager

    # Grammar rules

    def p_command_line(self, p):
        """command_line : starting_expression pipes_chain"""
        self.return_value = self._pipe_value

    def p_starting_expression(self, p):
        """starting_expression : PLAIN_STR
                               | quoted_str
                               | array
                               | command_call_no_parentheses
                               | command_call_with_parentheses"""
        p[0] = p[1]
        self._pipe_value = p[0]

    def p_pipes_chain(self, p):
        """pipes_chain : empty
           pipes_chain : pipe_expression
           pipes_chain : pipes_chain pipe_expression"""
        p[0] = self._create_list(p)

    def p_pipe_expression_no_parentheses(self, p):
        """pipe_expression : PIPE COMMAND argument_list
           pipe_expression : PIPE COMMAND LPAREN argument_list RPAREN"""
        if len(p) == 4:
            new_args = [self._pipe_value, *p[3]]
        else:
            new_args = [self._pipe_value, *p[4]]
        p[0] = self.command_manager.call_strings(p[2], new_args)
        self._pipe_value = p[0]

    def p_call_command_no_parentheses(self, p):
        """command_call_no_parentheses : COMMAND argument_list"""
        p[0] = self.command_manager.call_strings(p[1], p[2])

    def p_call_command_with_parentheses(self, p):
        """command_call_with_parentheses : COMMAND LPAREN argument_list RPAREN"""
        p[0] = self.command_manager.call_strings(p[1], p[3])

    def p_argument_list(self, p):
        """argument_list : empty
                         | argument
                         | argument_list argument"""
        p[0] = self._create_list(p)

    def p_argument(self, p):
        """argument : PLAIN_STR
                    | quoted_str
                    | array
                    | COMMAND
                    | command_call_with_parentheses"""
        p[0] = p[1]

    def p_array(self, p):
        """array : LBRACE argument_list RBRACE"""
        p[0] = ",".join(p[2]) if p[2] else ""

    def p_quoted_str(self, p):
        """quoted_str : QUOTED_STR"""
        p[0] = p[1].strip("'\"")

    def p_empty(self, p):
        """empty :"""

    def p_error(self, p):
        if p is None:
            raise exceptions.CommandError("Syntax error at EOF")
        else:
            raise exceptions.CommandError(f"Syntax error at '{p.value}'")

    @staticmethod
    def _create_list(p: yacc.YaccProduction) -> typing.List[typing.Any]:
        if len(p) == 2:
            p[0] = [] if p[1] is None else [p[1]]
        else:
            p[0] = p[1]
            p[0].append(p[2])
        return p[0]

    def build(self, **kwargs) -> None:
        self.parser = yacc.yacc(module=self,
                                errorlog=yacc.NullLogger(), **kwargs)

    def parse(self, lexer: lex.Lexer, **kwargs) -> typing.Any:
        self.parser.parse(lexer=lexer, **kwargs)
        self._pipe_value = None
        return self.return_value


def create_parser(
        command_manager: "mitmproxy.command.CommandManager"
) -> CommandLanguageParser:
    command_parser = CommandLanguageParser(command_manager)
    command_parser.build(debug=False, write_tables=False)
    return command_parser
