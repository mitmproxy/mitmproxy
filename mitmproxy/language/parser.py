import typing

import ply.lex as lex
import ply.yacc as yacc

import mitmproxy.command  # noqa
from mitmproxy import exceptions
from mitmproxy.language.lexer import CommandLanguageLexer


ParsedEntity = typing.Union[str, list, "ParsedCommand"]


ParsedCommand = typing.NamedTuple(
    "ParsedCommand",
    [
        ("command", "mitmproxy.command.Command"),
        ("args", typing.List[ParsedEntity])
    ]
)


class CommandLanguageParser:
    # the list of possible tokens is always required
    tokens = CommandLanguageLexer.tokens

    def __init__(self,
                 command_manager: "mitmproxy.command.CommandManager") -> None:
        self.parsed_line: ParsedEntity = None
        self._parsed_pipe_elem: ParsedCommand = None
        self.async_exec: bool = False
        self.command_manager = command_manager

    # Grammar rules

    def p_command_line(self, p):
        """command_line : starting_expression pipes_chain"""
        self.parsed_line = self._parsed_pipe_elem

    def p_starting_expression(self, p):
        """starting_expression : PLAIN_STR
                               | quoted_str
                               | array
                               | command_call_no_parentheses
                               | command_call_with_parentheses"""
        p[0] = p[1]
        self._parsed_pipe_elem = p[0]

    def p_pipes_chain(self, p):
        """pipes_chain : empty
           pipes_chain : pipe_expression
           pipes_chain : pipes_chain pipe_expression"""
        p[0] = self._create_list(p)

    def p_pipe_expression(self, p):
        """pipe_expression : PIPE COMMAND argument_list
           pipe_expression : PIPE COMMAND LPAREN argument_list RPAREN"""
        if len(p) == 4:
            new_args = [self._parsed_pipe_elem, *p[3]]
        else:
            new_args = [self._parsed_pipe_elem, *p[4]]
        p[0] = self._call_command(p[2], new_args)
        self._parsed_pipe_elem = p[0]

    def p_command_call_no_parentheses(self, p):
        """command_call_no_parentheses : COMMAND argument_list"""
        p[0] = self._call_command(p[1], p[2])

    def p_command_call_with_parentheses(self, p):
        """command_call_with_parentheses : COMMAND LPAREN argument_list RPAREN"""
        p[0] = self._call_command(p[1], p[3])

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
        p[0] = p[2]

    def p_quoted_str(self, p):
        """quoted_str : QUOTED_STR"""
        p[0] = p[1].strip("'\"")

    def p_empty(self, p):
        """empty :"""

    def p_error(self, p):
        self._reset_internals()
        if p is None:
            raise exceptions.CommandError("Syntax error at EOF")
        else:
            raise exceptions.CommandError(f"Syntax error at '{p.value}'")

    # Supporting methods

    def _call_command(self, command: str,
                      args: typing.List[ParsedEntity]) -> ParsedCommand:
        cmd = self.command_manager.get_command_by_path(command)
        if self.async_exec:
            ret = ParsedCommand(cmd, args)
        else:
            if cmd.asyncf:
                self._reset_internals()
                raise exceptions.ExecutionError(f"You are trying to run async "
                                                f"command '{command}' through sync executor.")
            else:
                ret = cmd.call(args)
        return ret

    def _reset_internals(self):
        self._parsed_pipe_elem = None
        self.async_exec = False

    @staticmethod
    def _create_list(p: yacc.YaccProduction) -> typing.List[ParsedEntity]:
        if len(p) == 2:
            p[0] = [] if p[1] is None else [p[1]]
        else:
            p[0] = p[1]
            p[0].append(p[2])
        return p[0]

    def build(self, **kwargs) -> None:
        self.parser = yacc.yacc(module=self,
                                errorlog=yacc.NullLogger(), **kwargs)

    def parse(self, lexer: lex.Lexer,
              async_exec: bool=False, **kwargs) -> typing.Any:
        self.async_exec = async_exec
        self.parser.parse(lexer=lexer, **kwargs)
        self._reset_internals()
        return self.parsed_line


def create_parser(
        command_manager: "mitmproxy.command.CommandManager"
) -> CommandLanguageParser:
    command_parser = CommandLanguageParser(command_manager)
    command_parser.build(debug=False, write_tables=False)
    return command_parser
