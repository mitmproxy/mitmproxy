
import abc

import contrib.pyparsing as pp

import netlib.websockets
from netlib import http_status
from . import base, generators, exceptions


class WS(base.CaselessLiteral):
    TOK = "ws"


class Raw(base.CaselessLiteral):
    TOK = "r"


class Path(base.SimpleValue):
    pass


class Method(base.OptionsOrValue):
    options = [
        "get",
        "head",
        "post",
        "put",
        "delete",
        "options",
        "trace",
        "connect",
    ]


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


class _HTTPMessage(base._Message):
    version = "HTTP/1.1"
    @property
    def raw(self):
        return bool(self.tok(Raw))


    @abc.abstractmethod
    def preamble(self, settings): # pragma: no cover
        pass

    def values(self, settings):
        vals = self.preamble(settings)
        vals.append("\r\n")
        for h in self.headers:
            vals.extend(h.values(settings))
        vals.append("\r\n")
        if self.body:
            vals.append(self.body.value.get_generator(settings))
        return vals


class Response(_HTTPMessage):
    comps = (
        base.Body,
        base.Header,
        base.PauseAt,
        base.DisconnectAt,
        base.InjectAt,
        base.ShortcutContentType,
        base.ShortcutLocation,
        Raw,
        base.Reason
    )
    logattrs = ["code", "reason", "version", "body"]

    @property
    def ws(self):
        return self.tok(WS)

    @property
    def code(self):
        return self.tok(base.Code)

    @property
    def reason(self):
        return self.tok(base.Reason)

    def preamble(self, settings):
        l = [self.version, " "]
        l.extend(self.code.values(settings))
        code = int(self.code.code)
        l.append(" ")
        if self.reason:
            l.extend(self.reason.values(settings))
        else:
            l.append(
                generators.LiteralGenerator(
                    http_status.RESPONSES.get(
                        code,
                        "Unknown code"
                    )
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
                    base.Code(101)
                )
            hdrs = netlib.websockets.server_handshake_headers(
                settings.websocket_key
            )
            for i in hdrs.lst:
                if not get_header(i[0], self.headers):
                    tokens.append(
                        base.Header(
                            base.ValueLiteral(i[0]),
                            base.ValueLiteral(i[1]))
                    )
        if not self.raw:
            if not get_header("Content-Length", self.headers):
                if not self.body:
                    length = 0
                else:
                    length = len(self.body.value.get_generator(settings))
                tokens.append(
                    base.Header(
                        base.ValueLiteral("Content-Length"),
                        base.ValueLiteral(str(length)),
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
                            base.Sep + base.Code.expr()
                        ),
                        base.Code.expr(),
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
        base.Body,
        base.Header,
        base.PauseAt,
        base.DisconnectAt,
        base.InjectAt,
        base.ShortcutContentType,
        base.ShortcutUserAgent,
        Raw,
        base.PathodSpec,
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
        return self.tok(base.PathodSpec)

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
                        base.Header(
                            base.ValueLiteral(i[0]),
                            base.ValueLiteral(i[1])
                        )
                    )
        if not self.raw:
            if not get_header("Content-Length", self.headers):
                if self.body:
                    length = len(self.body.value.get_generator(settings))
                    tokens.append(
                        base.Header(
                            base.ValueLiteral("Content-Length"),
                            base.ValueLiteral(str(length)),
                        )
                    )
            if settings.request_host:
                if not get_header("Host", self.headers):
                    tokens.append(
                        base.Header(
                            base.ValueLiteral("Host"),
                            base.ValueLiteral(settings.request_host)
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
        base.Code("800"),
        base.Header(
            base.ValueLiteral("Content-Type"),
            base.ValueLiteral("text/plain")
        ),
        base.Reason(base.ValueLiteral(reason)),
        base.Body(base.ValueLiteral("pathod error: " + (body or reason))),
    ]
    return PathodErrorResponse(tokens)
