import os
import netlib.http2
import pyparsing as pp
from . import base, generators, actions, message

"""
    Normal HTTP requests:
        <method>:<path>:<header>:<body>
    e.g.:
        GET:/
        GET:/:foo=bar
        POST:/:foo=bar:'content body payload'

    Individual HTTP/2 frames:
        h2f:<payload_length>:<type>:<flags>:<stream_id>:<payload>
    e.g.:
        h2f:0:PING
        h2f:42:HEADERS:END_HEADERS:0x1234567:foo=bar,host=example.com
        h2f:42:DATA:END_STREAM,PADDED:0x1234567:'content body payload'
"""


class Method(base.OptionsOrValue):
    options = [
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "DELETE",
    ]


class Path(base.Value):
    pass


class Header(base.KeyValue):
    preamble = "h"


class Body(base.Value):
    preamble = "b"


class Times(base.Integer):
    preamble = "x"


class Request(message.Message):
    comps = (
        Header,
        Body,

        Times,
    )

    @property
    def method(self):
        return self.tok(Method)

    @property
    def path(self):
        return self.tok(Path)

    @property
    def headers(self):
        return self.toks(Header)

    @property
    def body(self):
        return self.tok(Body)

    @property
    def times(self):
        return self.tok(Times)

    @property
    def actions(self):
        return []

    @classmethod
    def expr(klass):
        parts = [i.expr() for i in klass.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                Method.expr(),
                base.Sep,
                Path.expr(),
                base.Sep,
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(klass)
        return resp

    def resolve(self, settings, msg=None):
        tokens = self.tokens[:]
        return self.__class__(
            [i.resolve(settings, self) for i in tokens]
        )

    def values(self, settings):
        return settings.protocol.create_request(
            self.method.value.get_generator(settings),
            self.path,
            self.headers,
            self.body)

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


# class H2F(base.CaselessLiteral):
#     TOK = "h2f"
#
#
# class WebsocketFrame(message.Message):
#     pass
