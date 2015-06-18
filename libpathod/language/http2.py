import pyparsing as pp
from . import base, actions, message

"""
    Normal HTTP requests:
        <method>:<path>:<header>:<body>
    e.g.:
        GET:/
        GET:/:h"foo"="bar"
        POST:/:h"foo"="bar":b'content body payload'

    Normal HTTP responses:
        <code>:<header>:<body>
    e.g.:
        200
        302:h"foo"="bar"
        404:h"foo"="bar":b'content body payload'

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
    unique_name = None
    preamble = "h"

    def values(self, settings):
        return (
            self.key.get_generator(settings),
            self.value.get_generator(settings),
        )


class Body(base.Value):
    preamble = "b"


class Times(base.Integer):
    preamble = "x"


class Code(base.Integer):
    pass


class Request(message.Message):
    comps = (
        Header,
        Body,
        Times,
    )
    logattrs = ["method", "path"]

    def __init__(self, tokens):
        super(Request, self).__init__(tokens)
        self.rendered_values = None

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
    def expr(cls):
        parts = [i.expr() for i in cls.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                Method.expr(),
                base.Sep,
                Path.expr(),
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(cls)
        return resp

    def resolve(self, settings, msg=None):
        return self

    def values(self, settings):
        if self.rendered_values:
            return self.rendered_values
        else:
            headers = [header.values(settings) for header in self.headers]

            body = self.body
            if body:
                body = body.string()

            self.rendered_values = settings.protocol.create_request(
                self.method.string(),
                self.path.string(),
                headers,  # TODO: parse that into a dict?!
                body)
            return self.rendered_values

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


class Response(message.Message):
    unique_name = None
    comps = (
        Header,
        Body,
    )

    def __init__(self, tokens):
        super(Response, self).__init__(tokens)
        self.rendered_values = None
        self.stream_id = 0

    @property
    def code(self):
        return self.tok(Code)

    @property
    def headers(self):
        return self.toks(Header)

    @property
    def body(self):
        return self.tok(Body)

    @property
    def actions(self):
        return []

    def resolve(self, settings, msg=None):
        return self

    @classmethod
    def expr(cls):
        parts = [i.expr() for i in cls.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                Code.expr(),
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(cls)
        return resp

    def values(self, settings):
        if self.rendered_values:
            return self.rendered_values
        else:
            headers = [header.values(settings) for header in self.headers]

            body = self.body
            if body:
                body = body.string()

            self.rendered_values = settings.protocol.create_response(
                self.code.string(),
                self.stream_id,
                headers,  # TODO: parse that into a dict?!
                body)
            return self.rendered_values

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


def make_error_response(reason, body=None):
    tokens = [
        Code("800"),
        Body(base.TokValueLiteral("pathod error: " + (body or reason))),
    ]
    return Response(tokens)


# class Frame(message.Message):
#     pass
