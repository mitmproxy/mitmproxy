import typing

import ply.lex as lex
import ply.yacc as yacc

from mitmproxy import exceptions
from mitmproxy.language import markup_structures as ms
from mitmproxy.language.lexer import CommandLanguageLexer


class InteractivePartialParser:
    # the list of possible tokens is always required
    tokens = CommandLanguageLexer.tokens

    def __init__(self, manager):
        self.manager = manager
        self.parsed_line = None

    def p_command_call(self, p):
        """command_line : empty
                        | expression optional_pipes"""
        if len(p) == 2:
            space = p[1:]
        else:
            space = [p[1], *p[2]]
        self.parsed_line = ms.CommandLine(space)

    def p_expression(self, p):
        """expression : array
                      | command_call_no_parentheses
                      | command_call_with_parentheses"""
        p[0] = p[1]

    def p_pipes(self, p):
        """optional_pipes : pipe_expression optional_pipes
           optional_pipes : pipe_expression"""
        p[0] = p[1]

    def p_pipe_expression(self, p):
        """pipe_expression : empty
                           | PIPE
                           | PIPE command_call"""
        p[0] = [p[1]] if p[1] else []
        if len(p) > 2:
            p[0].append(p[2])

    def p_command_calll(self, p):
        """command_call : command_call_no_parentheses
                        | command_call_with_parentheses"""
        p[0] = p[1]

    def p_command_call_with_parentheses(self, p):
        """command_call_with_parentheses : command_name LPAREN
           command_call_with_parentheses : command_name LPAREN argument_list
           command_call_with_parentheses : command_name LPAREN argument_list RPAREN"""
        if len(p) == 3:
            space = {"head": p[2:3], "autoclosing": True}
        elif len(p) == 4:
            space = {"head": p[2:3], "arguments": p[3], "autoclosing": True}
        elif len(p) == 5:
            space = {"head": p[2:3], "arguments": p[3], "tail": p[4:5]}
        p[0] = ms.CommandSpace(p[1], self.manager, **space)

    def p_c(self, p):
        """command_call_with_parentheses : command_name LPAREN RPAREN"""
        space = {"head": p[2:]}
        p[0] = ms.CommandSpace(p[1], self.manager, **space)

    def p_command_call_no_parentheses(self, p):
        """command_call_no_parentheses : command_name argument_list"""
        args = {"arguments": p[2]}
        p[0] = ms.CommandSpace(p[1], self.manager, **args)

    def p_array(self, p):
        """array : LBRACE
           array : LBRACE RBRACE
           array : LBRACE argument_list
           array : LBRACE argument_list RBRACE"""
        if len(p) == 2:
            p[0] = ms.Array(space=p[1:], autoclosing=True)
        elif len(p) == 3:
            p[0] = ms.Array(space=p[1:])
        else:
            p[0] = ms.Array(space=[p[1], *p[2], p[3]])

    def p_argument_list(self, p):
        """argument_list : empty
                         | argument
                         | argument_list argument"""
        if len(p) == 2:
            p[0] = [] if p[1] is None else [p[1]]
        else:
            p[0] = p[1]
            p[0].append(p[2])

    def p_argument(self, p):
        """argument : DUMMY
                    | PLAIN_STR
                    | QUOTED_STR
                    | COMMAND
                    | array
                    | command_call_with_parentheses"""
        p[0] = p[1]

    def p_command_name(self, p):
        """command_name : DUMMY
                        | PLAIN_STR
                        | COMMAND"""
        p[0] = p[1]

    def p_empty(self, p):
        """empty :"""

    def p_error(self, p):
        raise exceptions.CommandError("Syntax error")

    def build(self, **kwargs):
        self.parser = yacc.yacc(module=self,
                                errorlog=yacc.NullLogger(), **kwargs)

    def parse(self, lexer: lex.Lexer, **kwargs) -> typing.Any:
        self.parser.parse(lexer=lexer, **kwargs)
        return self.parsed_line


def create_partial_parser(manager) -> InteractivePartialParser:
    command_parser = InteractivePartialParser(manager)
    command_parser.build(debug=False, write_tables=False)
    return command_parser