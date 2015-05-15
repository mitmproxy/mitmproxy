
import abc

import pyparsing as pp

import netlib.websockets
from netlib import http_status, http_uastrings
from . import base, exceptions, actions, message


class WS(base.CaselessLiteral):
    TOK = "ws"


class Raw(base.CaselessLiteral):
    TOK = "r"


class Path(base.Value):
    pass


class Code(base.Integer):
    pass


class Reason(base.Value):
    preamble = "m"


class Body(base.Value):
    preamble = "b"


class Method(base.OptionsOrValue):
    options = [
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS",
        "TRACE",
        "CONNECT",
    ]


class _HeaderMixin(object):
    def format_header(self, key, value):
        return [key, ": ", value, "\r\n"]

    def values(self, settings):
        return self.format_header(
            self.key.get_generator(settings),
            self.value.get_generator(settings),
        )


class Header(_HeaderMixin, base.KeyValue):
    preamble = "h"


class ShortcutContentType(_HeaderMixin, base.Value):
    preamble = "c"
    key = base.TokValueLiteral("Content-Type")


class ShortcutLocation(_HeaderMixin, base.Value):
    preamble = "l"
    key = base.TokValueLiteral("Location")


class ShortcutUserAgent(_HeaderMixin, base.OptionsOrValue):
    preamble = "u"
    options = [i[1] for i in http_uastrings.UASTRINGS]
    key = base.TokValueLiteral("User-Agent")

    def values(self, settings):
        if self.option_used:
            value = http_uastrings.get_by_shortcut(
                self.value.val.lower()
            )[2]
        else:
            value = self.value.val
        return self.format_header(
            self.key.get_generator(settings),
            value
        )


class PathodResponse(base.Token):
    def __init__(self, value):
        self.value = value
        try:
            self.parsed = Response(
                Response.expr().parseString(
                    value.val,
                    parseAll=True
                )
            )
        except pp.ParseException, v:
            raise exceptions.ParseException(v.msg, v.line, v.col)

    @classmethod
    def expr(klass):
        e = pp.Literal("s").suppress()
        e = e + base.TokValueLiteral.expr()
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [
            self.value.get_generator(settings),
        ]

    def spec(self):
        return "s%s"%(self.value.spec())

    def freeze(self, settings):
        f = self.parsed.freeze(settings).spec()
        return PathodResponse(base.TokValueLiteral(f.encode("string_escape")))


def get_header(val, headers):
    """
        Header keys may be Values, so we have to "generate" them as we try the
        match.
    """
    for h in headers:
        k = h.key.get_generator({})
        if len(k) == len(val) and k[:].lower() == val.lower():
            return h
    return None


class _HTTPMessage(message.Message):
    version = "HTTP/1.1"
    @property
    def actions(self):
        return self.toks(actions._Action)

    @property
    def raw(self):
        return bool(self.tok(Raw))

    @property
    def body(self):
        return self.tok(Body)

    @abc.abstractmethod
    def preamble(self, settings): # pragma: no cover
        pass

    @property
    def headers(self):
        return self.toks(_HeaderMixin)

    def values(self, settings):
        vals = self.preamble(settings)
        vals.append("\r\n")
        for h in self.headers:
            vals.extend(h.values(settings))
        vals.append("\r\n")
        if self.body:
            vals.extend(self.body.values(settings))
        return vals


class Response(_HTTPMessage):
    comps = (
        Body,
        Header,
        ShortcutContentType,
        ShortcutLocation,
        Raw,
        Reason,

        actions.PauseAt,
        actions.DisconnectAt,
        actions.InjectAt,
    )
    logattrs = ["code", "reason", "version", "body"]

    @property
    def ws(self):
        return self.tok(WS)

    @property
    def code(self):
        return self.tok(Code)

    @property
    def reason(self):
        return self.tok(Reason)

    def preamble(self, settings):
        l = [self.version, " "]
        l.extend(self.code.values(settings))
        code = int(self.code.value)
        l.append(" ")
        if self.reason:
            l.extend(self.reason.values(settings))
        else:
            l.append(
                http_status.RESPONSES.get(
                    code,
                    "Unknown code"
                )
            )
        return l

    def resolve(self, settings, msg=None):
        tokens = self.tokens[:]
        if self.ws:
            if not settings.websocket_key:
                raise exceptions.RenderError(
                    "No websocket key - have we seen a client handshake?"
                )
            if not self.code:
                tokens.insert(
                    1,
                    Code(101)
                )
            hdrs = netlib.websockets.server_handshake_headers(
                settings.websocket_key
            )
            for i in hdrs.lst:
                if not get_header(i[0], self.headers):
                    tokens.append(
                        Header(
                            base.TokValueLiteral(i[0]),
                            base.TokValueLiteral(i[1]))
                    )
        if not self.raw:
            if not get_header("Content-Length", self.headers):
                if not self.body:
                    length = 0
                else:
                    length = sum(
                        len(i) for i in self.body.values(settings)
                    )
                tokens.append(
                    Header(
                        base.TokValueLiteral("Content-Length"),
                        base.TokValueLiteral(str(length)),
                    )
                )
        intermediate = self.__class__(tokens)
        return self.__class__(
            [i.resolve(settings, intermediate) for i in tokens]
        )

    @classmethod
    def expr(klass):
        parts = [i.expr() for i in klass.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                pp.MatchFirst(
                    [
                        WS.expr() + pp.Optional(
                            base.Sep + Code.expr()
                        ),
                        Code.expr(),
                    ]
                ),
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(klass)
        return resp

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


class Request(_HTTPMessage):
    comps = (
        Body,
        Header,
        ShortcutContentType,
        ShortcutUserAgent,
        Raw,
        PathodResponse,

        actions.PauseAt,
        actions.DisconnectAt,
        actions.InjectAt,
    )
    logattrs = ["method", "path", "body"]

    @property
    def ws(self):
        return self.tok(WS)

    @property
    def method(self):
        return self.tok(Method)

    @property
    def path(self):
        return self.tok(Path)

    @property
    def pathodspec(self):
        return self.tok(PathodResponse)

    def preamble(self, settings):
        v = self.method.values(settings)
        v.append(" ")
        v.extend(self.path.values(settings))
        if self.pathodspec:
            v.append(self.pathodspec.parsed.spec())
        v.append(" ")
        v.append(self.version)
        return v

    def resolve(self, settings, msg=None):
        tokens = self.tokens[:]
        if self.ws:
            if not self.method:
                tokens.insert(
                    1,
                    Method("get")
                )
            for i in netlib.websockets.client_handshake_headers().lst:
                if not get_header(i[0], self.headers):
                    tokens.append(
                        Header(
                            base.TokValueLiteral(i[0]),
                            base.TokValueLiteral(i[1])
                        )
                    )
        if not self.raw:
            if not get_header("Content-Length", self.headers):
                if self.body:
                    length = sum(
                        len(i) for i in self.body.values(settings)
                    )
                    tokens.append(
                        Header(
                            base.TokValueLiteral("Content-Length"),
                            base.TokValueLiteral(str(length)),
                        )
                    )
            if settings.request_host:
                if not get_header("Host", self.headers):
                    tokens.append(
                        Header(
                            base.TokValueLiteral("Host"),
                            base.TokValueLiteral(settings.request_host)
                        )
                    )
        intermediate = self.__class__(tokens)
        return self.__class__(
            [i.resolve(settings, intermediate) for i in tokens]
        )

    @classmethod
    def expr(klass):
        parts = [i.expr() for i in klass.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                pp.MatchFirst(
                    [
                        WS.expr() + pp.Optional(
                            base.Sep + Method.expr()
                        ),
                        Method.expr(),
                    ]
                ),
                base.Sep,
                Path.expr(),
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(klass)
        return resp

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


class PathodErrorResponse(Response):
    pass


def make_error_response(reason, body=None):
    tokens = [
        Code("800"),
        Header(
            base.TokValueLiteral("Content-Type"),
            base.TokValueLiteral("text/plain")
        ),
        Reason(base.TokValueLiteral(reason)),
        Body(base.TokValueLiteral("pathod error: " + (body or reason))),
    ]
    return PathodErrorResponse(tokens)
