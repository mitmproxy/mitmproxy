from enum import Enum
import io
from typing import Union, List


class State(Enum):
    QUOTE = 1
    ESCAPE = 2
    TEXT = 3


class Lexer:

    def __init__(self, text: Union[str, io.StringIO]) -> None:
        self._count = 0
        self._parsed = False

        self._state = State.TEXT
        self._states: List[State] = []
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
        except ValueError:
            raise

    def parse(self):
        acc = ''
        quote = ''
        self._state = State.TEXT

        whitespace = "\r\n\t "

        self.text.seek(self._text_pos)

        while True:
            ch = self.text.read(1)
            self._text_pos += 1

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
                if ch in whitespace:
                    if acc != '':
                        break
                elif ch == '"' or ch == "'":
                    quote = ch
                    self._quote_start_pos = self._text_pos
                    self._states.append(self._state)
                    self._state = State.QUOTE
                    acc += ch
                elif ch == '\\':
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
