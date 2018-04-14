import io
import re
import textwrap
from typing import Iterable

from mitmproxy.contentviews import base
from mitmproxy.utils import sliding_window

"""
A custom XML/HTML prettifier. Compared to other prettifiers, its main features are:

- Implemented in pure Python.
- Modifies whitespace only.
- Works with any input.
- Lazy evaluation.

The implementation is split into two main parts: tokenization and formatting of tokens.
"""

# http://www.xml.com/pub/a/2001/07/25/namingparts.html - this is close enough for what we do.
REGEX_TAG = re.compile("[a-zA-Z0-9._:\-]+(?!=)")
# https://www.w3.org/TR/html5/syntax.html#void-elements
HTML_VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "keygen", "link", "meta", "param",
    "source", "track", "wbr"
}
NO_INDENT_TAGS = {"xml", "doctype", "html"}
INDENT = 2


class Token:
    def __init__(self, data):
        self.data = data

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            self.data
        )


class Text(Token):
    @property
    def text(self):
        return self.data.strip()


class Tag(Token):
    @property
    def tag(self):
        t = REGEX_TAG.search(self.data)
        if t is not None:
            return t.group(0).lower()
        return "<empty>"

    @property
    def is_comment(self) -> bool:
        return self.data.startswith("<!--")

    @property
    def is_cdata(self) -> bool:
        return self.data.startswith("<![CDATA[")

    @property
    def is_closing(self):
        return self.data.startswith("</")

    @property
    def is_self_closing(self):
        return self.is_comment or self.is_cdata or self.data.endswith(
            "/>") or self.tag in HTML_VOID_ELEMENTS

    @property
    def is_opening(self):
        return not self.is_closing and not self.is_self_closing

    @property
    def done(self):
        if self.is_comment:
            return self.data.endswith("-->")
        elif self.is_cdata:
            return self.data.endswith("]]>")
        else:
            # This fails for attributes that contain an unescaped ">"
            return self.data.endswith(">")


def tokenize(data: str) -> Iterable[Token]:
    token: Token = Text("")

    i = 0

    def readuntil(char, start, include=1):
        nonlocal i
        end = data.find(char, start)
        if end == -1:
            end = len(data)
        ret = data[i:end + include]
        i = end + include
        return ret

    while i < len(data):
        if isinstance(token, Text):
            token.data = readuntil("<", i, 0)
            if token.text:
                yield token
            token = Tag("")
        elif isinstance(token, Tag):
            token.data += readuntil(">", i, 1)
            if token.done:
                yield token
                token = Text("")
    if token.data.strip():
        yield token


def indent_text(data: str, prefix: str) -> str:
    # Add spacing to first line so that we dedent in cases like this:
    # <li>This is
    #     example text
    #     over multiple lines
    # </li>
    dedented = textwrap.dedent(" " * 32 + data).strip()
    return textwrap.indent(dedented, prefix[:32])


def is_inline_text(a: Token, b: Token, c: Token) -> bool:
    if isinstance(a, Tag) and isinstance(b, Text) and isinstance(c, Tag):
        if a.is_opening and "\n" not in b.data and c.is_closing and a.tag == c.tag:
            return True
    return False


def is_inline(prev2: Token, prev1: Token, t: Token, next1: Token, next2: Token) -> bool:
    if isinstance(t, Text):
        return is_inline_text(prev1, t, next1)
    elif isinstance(t, Tag):
        if is_inline_text(prev2, prev1, t) or is_inline_text(t, next1, next2):
            return True
        if isinstance(next1, Tag) and t.is_opening and next1.is_closing and t.tag == next1.tag:
                return True  # <div></div> (start tag)
        if isinstance(prev1, Tag) and prev1.is_opening and t.is_closing and prev1.tag == t.tag:
            return True  # <div></div> (end tag)
    return False


class ElementStack:
    """
    Keep track of how deeply nested our document is.
    """

    def __init__(self):
        self.open_tags = []
        self.indent = ""

    def push_tag(self, tag: str):
        if len(self.open_tags) > 16:
            return
        self.open_tags.append(tag)
        if tag not in NO_INDENT_TAGS:
            self.indent += " " * INDENT

    def pop_tag(self, tag: str):
        if tag in self.open_tags:
            remove_indent = 0
            while True:
                t = self.open_tags.pop()
                if t not in NO_INDENT_TAGS:
                    remove_indent += INDENT
                if t == tag:
                    break
            self.indent = self.indent[:-remove_indent]
        else:
            pass  # this closing tag has no start tag. let's keep indentation as-is.


def format_xml(tokens: Iterable[Token]) -> str:
    out = io.StringIO()

    context = ElementStack()

    for prev2, prev1, token, next1, next2 in sliding_window.window(tokens, 2, 2):
        if isinstance(token, Tag):
            if token.is_opening:
                out.write(indent_text(token.data, context.indent))

                if not is_inline(prev2, prev1, token, next1, next2):
                    out.write("\n")

                context.push_tag(token.tag)
            elif token.is_closing:
                context.pop_tag(token.tag)

                if is_inline(prev2, prev1, token, next1, next2):
                    out.write(token.data)
                else:
                    out.write(indent_text(token.data, context.indent))
                out.write("\n")

            else:  # self-closing
                out.write(indent_text(token.data, context.indent))
                out.write("\n")
        elif isinstance(token, Text):
            if is_inline(prev2, prev1, token, next1, next2):
                out.write(token.text)
            else:
                out.write(indent_text(token.data, context.indent))
                out.write("\n")
        else:  # pragma: no cover
            raise RuntimeError()

    return out.getvalue()


class ViewXmlHtml(base.View):
    name = "XML/HTML"
    content_types = ["text/xml", "text/html"]

    def __call__(self, data, **metadata):
        # TODO:
        # We should really have the message text as str here,
        # not the message content as bytes.
        # https://github.com/mitmproxy/mitmproxy/issues/1662#issuecomment-266192578
        data = data.decode("utf8", "xmlcharrefreplace")
        tokens = tokenize(data)
        # TODO:
        # Performance: Don't render the whole document right away.
        # Let's wait with this until we have a sequence-like interface,
        # this thing is reasonably fast right now anyway.
        pretty = base.format_text(format_xml(tokens))
        if "html" in data.lower():
            t = "HTML"
        else:
            t = "XML"
        return t, pretty
