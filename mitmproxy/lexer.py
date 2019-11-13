from enum import Enum
import io
from typing import Union
import pdb


class State(Enum):
    QUOTE = 1
    ESCAPE = 2
    TEXT = 3


class Lexer:

    def __init__(self, text: Union[str, io.StringIO]):
        self._tokens = []
        self._count = 0
        self._parsed = False

        self._state = State.TEXT
        self._states = []
        self._text_pos = 0
        self._quote_start_pos = 0

        if isinstance(text, str):
            self.text = io.StringIO(text)
        else:
            self.text = text

    def __iter__(self):
        return self

    def __next__(self):
        t = self.get_token()

        if t == '':
            raise StopIteration

        return t

    def get_token(self):

        try:
            return self.parse()
        except ValueError as e:
            raise

        if len(self._tokens) > 0:
            ret = self._tokens[0]
            self._tokens = self._tokens[1:]
        else:
            ret = None
        return ret

    #def get_remainder(self):
    #    try:
    #        self.parse()
    #    except ValueError as e:
    #        return self.text
    #        

    #    return ' '.join(self._tokens)

    def parse(self):
        acc = ''
        quote = '' # used by the parser
        tokens = []
        self._state = State.TEXT
        text = self.text
        i = 0

        #self.text.seek(self._text_pos)

        while True:
            ch = self.text.read(1)
            self._text_pos += 1

            #pdb.set_trace()


            # If this is the last char of the string, let's save the token
            if ch == '' or ch is None:
                break

            if self._state == State.QUOTE:
                if ch == '\\':
                    self._states.append(self._state)
                    self._state = State.ESCAPE
                    acc += ch
                elif ch == quote:
                    self._state = self._states.pop()
                    acc += ch
                else:
                    acc += ch

            elif self._state == State.ESCAPE:
                acc += ch
                self._state = self._states.pop()

            elif self._state == State.TEXT:
                if ch == ' ':
                    if acc != '':
                        break
                elif ch == '"' or ch == "'":
                    quote = ch
                    self._quote_start_pos = self._text_pos
                    self._states.append(self._state)
                    self._state = State.QUOTE
                    acc += ch
                elif ch == '\\':
                    # TODO: Does it make sense to go to State.ESCAPE from State.TEXT?
                    self._states.append(self._state)
                    self._state = State.ESCAPE
                    acc += ch
                else:
                    acc += ch
            else:
                print("This shouldn't have happened")
                exit(-1)

        self._token = acc

        if self._state == State.QUOTE:
            raise ValueError("No closing quotation for quote in position %d" % self._quote_start_pos)

        return self._token


if __name__ == '__main__':

    cases = []
    cases.append(r'abc')
    cases.append(r'Hello World')
    cases.append(r'"Hello \" World"')
    cases.append(r"'Hello \' World'")
    cases.append(r'"\""')
    cases.append(r'abc "def\" \x bla \z \\ \e \ " xpto')
    cases.append(r'')
    cases.append(r' ')
    cases.append(r'  ')
    cases.append(r'   ')
    cases.append(r'    ')
    cases.append(r'Hello World ')

    for s in cases:
        lex = Lexer(s)
        tokens = list(lex)

        if len(tokens) == 1:
            print('%s = %d token' % (str(tokens), len(tokens)))
        else:
            print('%s = %d tokens' % (str(tokens), len(tokens)))


