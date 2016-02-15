
import abc

import pyparsing as pp

import netlib.websockets
from netlib.http import status_codes, user_agents
from . import base, exceptions, actions, message

# TODO: use netlib.semantics.protocol assemble method,
# instead of duplicating the HTTP on-the-wire representation here.
# see http2 language for an example

class WS(base.CaselessLiteral):
    TOK = "ws"


class Raw(base.CaselessLiteral):
    TOK = "r"


class Path(base.Value):
    pass


class StatusCode(base.Integer):
    pass


class Reason(base.Value):
    preamble = "m"


class Body(base.Value):
    preamble = "b"


class Times(base.Integer):
    preamble = "x"


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
    unique_name = None

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
    options = [i[1] for i in user_agents.UASTRINGS]
    key = base.TokValueLiteral("User-Agent")

    def values(self, settings):
        value = self.value.val
        if self.option_used:
            value = user_agents.get_by_shortcut(value.lower())[2]

        return self.format_header(
            self.key.get_generator(settings),
            value
        )


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
    def preamble(self, settings):  # pragma: no cover
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
    unique_name = None
    comps = (
        Header,
        ShortcutContentType,
        ShortcutLocation,
        Raw,
        Reason,
        Body,

        actions.PauseAt,
        actions.DisconnectAt,
        actions.InjectAt,
    )
    logattrs = ["status_code", "reason", "version", "body"]

    @property
    def ws(self):
        return self.tok(WS)

    @property
    def status_code(self):
        return self.tok(StatusCode)

    @property
    def reason(self):
        return self.tok(Reason)

    def preamble(self, settings):
        l = [self.version, " "]
        l.extend(self.status_code.values(settings))
        status_code = int(self.status_code.value)
        l.append(" ")
        if self.reason:
            l.extend(self.reason.values(settings))
        else:
            l.append(
                status_codes.RESPONSES.get(
                    status_code,
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
            if not self.status_code:
                tokens.insert(
                    1,
                    StatusCode(101)
                )
            headers = netlib.websockets.WebsocketsProtocol.server_handshake_headers(
                settings.websocket_key
            )
            for i in headers.fields:
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
    def expr(cls):
        parts = [i.expr() for i in cls.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                pp.MatchFirst(
                    [
                        WS.expr() + pp.Optional(
                            base.Sep + StatusCode.expr()
                        ),
                        StatusCode.expr(),
                    ]
                ),
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(cls)
        return resp

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


class NestedResponse(base.NestedMessage):
    preamble = "s"
    nest_type = Response


class Request(_HTTPMessage):
    comps = (
        Header,
        ShortcutContentType,
        ShortcutUserAgent,
        Raw,
        NestedResponse,
        Body,
        Times,

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
    def times(self):
        return self.tok(Times)

    @property
    def nested_response(self):
        return self.tok(NestedResponse)

    def preamble(self, settings):
        v = self.method.values(settings)
        v.append(" ")
        v.extend(self.path.values(settings))
        if self.nested_response:
            v.append(self.nested_response.parsed.spec())
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
            for i in netlib.websockets.WebsocketsProtocol.client_handshake_headers().fields:
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
    def expr(cls):
        parts = [i.expr() for i in cls.comps]
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
        resp = resp.setParseAction(cls)
        return resp

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


def make_error_response(reason, body=None):
    tokens = [
        StatusCode("800"),
        Header(
            base.TokValueLiteral("Content-Type"),
            base.TokValueLiteral("text/plain")
        ),
        Reason(base.TokValueLiteral(reason)),
        Body(base.TokValueLiteral("pathod error: " + (body or reason))),
    ]
    return Response(tokens)
