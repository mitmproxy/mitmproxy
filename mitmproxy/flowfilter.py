"""
The following operators are understood:

    ~q          Request
    ~s          Response

Headers:

    Patterns are matched against "name: value" strings. Field names are
    all-lowercase.

    ~a          Asset content-type in response. Asset content types are:
                    text/javascript
                    application/x-javascript
                    application/javascript
                    text/css
                    image/*
                    font/*
                    application/font-*
    ~h rex      Header line in either request or response
    ~hq rex     Header in request
    ~hs rex     Header in response

    ~b rex      Expression in the body of either request or response
    ~bq rex     Expression in the body of request
    ~bs rex     Expression in the body of response
    ~t rex      Shortcut for content-type header.

    ~d rex      Request domain
    ~m rex      Method
    ~u rex      URL
    ~c CODE     Response code.
    rex         Equivalent to ~u rex
"""

import functools
import re
import sys
from collections.abc import Sequence
from typing import ClassVar
from typing import Protocol

import pyparsing as pp

from mitmproxy import dns
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import udp


def only(*types):
    def decorator(fn):
        @functools.wraps(fn)
        def filter_types(self, flow):
            if isinstance(flow, types):
                return fn(self, flow)
            return False

        return filter_types

    return decorator


class _Token:
    def dump(self, indent=0, fp=sys.stdout):
        print(
            "{spacing}{name}{expr}".format(
                spacing="\t" * indent,
                name=self.__class__.__name__,
                expr=getattr(self, "expr", ""),
            ),
            file=fp,
        )


class _Action(_Token):
    code: ClassVar[str]
    help: ClassVar[str]

    @classmethod
    def make(klass, s, loc, toks):
        return klass(*toks[1:])


class FErr(_Action):
    code = "e"
    help = "Match error"

    def __call__(self, f):
        return True if f.error else False


class FMarked(_Action):
    code = "marked"
    help = "Match marked flows"

    def __call__(self, f):
        return bool(f.marked)


class FHTTP(_Action):
    code = "http"
    help = "Match HTTP flows"

    @only(http.HTTPFlow)
    def __call__(self, f):
        return True


class FWebSocket(_Action):
    code = "websocket"
    help = "Match WebSocket flows"

    @only(http.HTTPFlow)
    def __call__(self, f: http.HTTPFlow):
        return f.websocket is not None


class FTCP(_Action):
    code = "tcp"
    help = "Match TCP flows"

    @only(tcp.TCPFlow)
    def __call__(self, f):
        return True


class FUDP(_Action):
    code = "udp"
    help = "Match UDP flows"

    @only(udp.UDPFlow)
    def __call__(self, f):
        return True


class FDNS(_Action):
    code = "dns"
    help = "Match DNS flows"

    @only(dns.DNSFlow)
    def __call__(self, f):
        return True


class FReq(_Action):
    code = "q"
    help = "Match request with no response"

    @only(http.HTTPFlow, dns.DNSFlow)
    def __call__(self, f):
        if not f.response:
            return True


class FResp(_Action):
    code = "s"
    help = "Match response"

    @only(http.HTTPFlow, dns.DNSFlow)
    def __call__(self, f):
        return bool(f.response)


class FAll(_Action):
    code = "all"
    help = "Match all flows"

    def __call__(self, f: flow.Flow):
        return True


class _Rex(_Action):
    flags = 0
    is_binary = True

    def __init__(self, expr):
        self.expr = expr
        if self.is_binary:
            expr = expr.encode()
        try:
            self.re = re.compile(expr, self.flags)
        except Exception:
            raise ValueError("Cannot compile expression.")


def _check_content_type(rex, message):
    return any(
        name.lower() == b"content-type" and rex.search(value)
        for name, value in message.headers.fields
    )


class FAsset(_Action):
    code = "a"
    help = "Match asset in response: CSS, JavaScript, images, fonts."
    ASSET_TYPES = [
        re.compile(x)
        for x in [
            b"text/javascript",
            b"application/x-javascript",
            b"application/javascript",
            b"text/css",
            b"image/.*",
            b"font/.*",
            b"application/font.*",
        ]
    ]

    @only(http.HTTPFlow)
    def __call__(self, f):
        if f.response:
            for i in self.ASSET_TYPES:
                if _check_content_type(i, f.response):
                    return True
        return False


class FContentType(_Rex):
    code = "t"
    help = "Content-type header"

    @only(http.HTTPFlow)
    def __call__(self, f):
        if _check_content_type(self.re, f.request):
            return True
        elif f.response and _check_content_type(self.re, f.response):
            return True
        return False


class FContentTypeRequest(_Rex):
    code = "tq"
    help = "Request Content-Type header"

    @only(http.HTTPFlow)
    def __call__(self, f):
        return _check_content_type(self.re, f.request)


class FContentTypeResponse(_Rex):
    code = "ts"
    help = "Response Content-Type header"

    @only(http.HTTPFlow)
    def __call__(self, f):
        if f.response:
            return _check_content_type(self.re, f.response)
        return False


class FHead(_Rex):
    code = "h"
    help = "Header"
    flags = re.MULTILINE

    @only(http.HTTPFlow)
    def __call__(self, f):
        if f.request and self.re.search(bytes(f.request.headers)):
            return True
        if f.response and self.re.search(bytes(f.response.headers)):
            return True
        return False


class FHeadRequest(_Rex):
    code = "hq"
    help = "Request header"
    flags = re.MULTILINE

    @only(http.HTTPFlow)
    def __call__(self, f):
        if f.request and self.re.search(bytes(f.request.headers)):
            return True


class FHeadResponse(_Rex):
    code = "hs"
    help = "Response header"
    flags = re.MULTILINE

    @only(http.HTTPFlow)
    def __call__(self, f):
        if f.response and self.re.search(bytes(f.response.headers)):
            return True


class FBod(_Rex):
    code = "b"
    help = "Body"
    flags = re.DOTALL

    @only(http.HTTPFlow, tcp.TCPFlow, udp.UDPFlow, dns.DNSFlow)
    def __call__(self, f):
        if isinstance(f, http.HTTPFlow):
            if (
                f.request
                and (content := f.request.get_content(strict=False)) is not None
            ):
                if self.re.search(content):
                    return True
            if (
                f.response
                and (content := f.response.get_content(strict=False)) is not None
            ):
                if self.re.search(content):
                    return True
            if f.websocket:
                for wmsg in f.websocket.messages:
                    if wmsg.content is not None and self.re.search(wmsg.content):
                        return True
        elif isinstance(f, (tcp.TCPFlow, udp.UDPFlow)):
            for msg in f.messages:
                if msg.content is not None and self.re.search(msg.content):
                    return True
        elif isinstance(f, dns.DNSFlow):
            if f.request and self.re.search(f.request.content):
                return True
            if f.response and self.re.search(f.response.content):
                return True
        return False


class FBodRequest(_Rex):
    code = "bq"
    help = "Request body"
    flags = re.DOTALL

    @only(http.HTTPFlow, tcp.TCPFlow, udp.UDPFlow, dns.DNSFlow)
    def __call__(self, f):
        if isinstance(f, http.HTTPFlow):
            if (
                f.request
                and (content := f.request.get_content(strict=False)) is not None
            ):
                if self.re.search(content):
                    return True
            if f.websocket:
                for wmsg in f.websocket.messages:
                    if wmsg.from_client and self.re.search(wmsg.content):
                        return True
        elif isinstance(f, (tcp.TCPFlow, udp.UDPFlow)):
            for msg in f.messages:
                if msg.from_client and self.re.search(msg.content):
                    return True
        elif isinstance(f, dns.DNSFlow):
            if f.request and self.re.search(f.request.content):
                return True


class FBodResponse(_Rex):
    code = "bs"
    help = "Response body"
    flags = re.DOTALL

    @only(http.HTTPFlow, tcp.TCPFlow, udp.UDPFlow, dns.DNSFlow)
    def __call__(self, f):
        if isinstance(f, http.HTTPFlow):
            if (
                f.response
                and (content := f.response.get_content(strict=False)) is not None
            ):
                if self.re.search(content):
                    return True
            if f.websocket:
                for wmsg in f.websocket.messages:
                    if not wmsg.from_client and self.re.search(wmsg.content):
                        return True
        elif isinstance(f, (tcp.TCPFlow, udp.UDPFlow)):
            for msg in f.messages:
                if not msg.from_client and self.re.search(msg.content):
                    return True
        elif isinstance(f, dns.DNSFlow):
            if f.response and self.re.search(f.response.content):
                return True


class FMethod(_Rex):
    code = "m"
    help = "Method"
    flags = re.IGNORECASE

    @only(http.HTTPFlow)
    def __call__(self, f):
        return bool(self.re.search(f.request.data.method))


class FDomain(_Rex):
    code = "d"
    help = "Domain"
    flags = re.IGNORECASE
    is_binary = False

    @only(http.HTTPFlow)
    def __call__(self, f):
        return bool(
            self.re.search(f.request.host) or self.re.search(f.request.pretty_host)
        )


class FUrl(_Rex):
    code = "u"
    help = "URL"
    is_binary = False
    flags = re.IGNORECASE

    # FUrl is special, because it can be "naked".

    @classmethod
    def make(klass, s, loc, toks):
        if len(toks) > 1:
            toks = toks[1:]
        return klass(*toks)

    @only(http.HTTPFlow, dns.DNSFlow)
    def __call__(self, f):
        if not f or not f.request:
            return False
        if isinstance(f, http.HTTPFlow):
            return self.re.search(f.request.pretty_url)
        elif isinstance(f, dns.DNSFlow):
            return f.request.questions and self.re.search(f.request.questions[0].name)


class FSrc(_Rex):
    code = "src"
    help = "Match source address"
    is_binary = False

    def __call__(self, f):
        if not f.client_conn or not f.client_conn.peername:
            return False
        r = f"{f.client_conn.peername[0]}:{f.client_conn.peername[1]}"
        return f.client_conn.peername and self.re.search(r)


class FDst(_Rex):
    code = "dst"
    help = "Match destination address"
    is_binary = False

    def __call__(self, f):
        if not f.server_conn or not f.server_conn.address:
            return False
        r = f"{f.server_conn.address[0]}:{f.server_conn.address[1]}"
        return f.server_conn.address and self.re.search(r)


class FReplay(_Action):
    code = "replay"
    help = "Match replayed flows"

    def __call__(self, f):
        return f.is_replay is not None


class FReplayClient(_Action):
    code = "replayq"
    help = "Match replayed client request"

    def __call__(self, f):
        return f.is_replay == "request"


class FReplayServer(_Action):
    code = "replays"
    help = "Match replayed server response"

    def __call__(self, f):
        return f.is_replay == "response"


class FMeta(_Rex):
    code = "meta"
    help = "Flow metadata"
    flags = re.MULTILINE
    is_binary = False

    def __call__(self, f):
        m = "\n".join([f"{key}: {value}" for key, value in f.metadata.items()])
        return self.re.search(m)


class FMarker(_Rex):
    code = "marker"
    help = "Match marked flows with specified marker"
    is_binary = False

    def __call__(self, f):
        return self.re.search(f.marked)


class FComment(_Rex):
    code = "comment"
    help = "Flow comment"
    flags = re.MULTILINE
    is_binary = False

    def __call__(self, f):
        return self.re.search(f.comment)


class _Int(_Action):
    def __init__(self, num):
        self.num = int(num)


class FCode(_Int):
    code = "c"
    help = "HTTP response code"

    @only(http.HTTPFlow)
    def __call__(self, f):
        if f.response and f.response.status_code == self.num:
            return True


class FAnd(_Token):
    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        super().dump(indent, fp)
        for i in self.lst:
            i.dump(indent + 1, fp)

    def __call__(self, f):
        return all(i(f) for i in self.lst)


class FOr(_Token):
    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        super().dump(indent, fp)
        for i in self.lst:
            i.dump(indent + 1, fp)

    def __call__(self, f):
        return any(i(f) for i in self.lst)


class FNot(_Token):
    def __init__(self, itm):
        self.itm = itm[0]

    def dump(self, indent=0, fp=sys.stdout):
        super().dump(indent, fp)
        self.itm.dump(indent + 1, fp)

    def __call__(self, f):
        return not self.itm(f)


filter_unary: Sequence[type[_Action]] = [
    FAsset,
    FErr,
    FHTTP,
    FMarked,
    FReplay,
    FReplayClient,
    FReplayServer,
    FReq,
    FResp,
    FTCP,
    FUDP,
    FDNS,
    FWebSocket,
    FAll,
]
filter_rex: Sequence[type[_Rex]] = [
    FBod,
    FBodRequest,
    FBodResponse,
    FContentType,
    FContentTypeRequest,
    FContentTypeResponse,
    FDomain,
    FDst,
    FHead,
    FHeadRequest,
    FHeadResponse,
    FMethod,
    FSrc,
    FUrl,
    FMeta,
    FMarker,
    FComment,
]
filter_int = [FCode]


def _make():
    # Order is important - multi-char expressions need to come before narrow
    # ones.
    parts = []
    for cls in filter_unary:
        f = pp.Literal(f"~{cls.code}") + pp.WordEnd()
        f.setParseAction(cls.make)
        parts.append(f)

    # This is a bit of a hack to simulate Word(pyparsing_unicode.printables),
    # which has a horrible performance with len(pyparsing.pyparsing_unicode.printables) == 1114060
    unicode_words = pp.CharsNotIn("()~'\"" + pp.ParserElement.DEFAULT_WHITE_CHARS)
    unicode_words.skipWhitespace = True
    regex = (
        unicode_words
        | pp.QuotedString('"', escChar="\\")
        | pp.QuotedString("'", escChar="\\")
    )
    for cls in filter_rex:
        f = pp.Literal(f"~{cls.code}") + pp.WordEnd() + regex.copy()
        f.setParseAction(cls.make)
        parts.append(f)

    for cls in filter_int:
        f = pp.Literal(f"~{cls.code}") + pp.WordEnd() + pp.Word(pp.nums)
        f.setParseAction(cls.make)
        parts.append(f)

    # A naked rex is a URL rex:
    f = regex.copy()
    f.setParseAction(FUrl.make)
    parts.append(f)

    atom = pp.MatchFirst(parts)
    expr = pp.infixNotation(
        atom,
        [
            (pp.Literal("!").suppress(), 1, pp.opAssoc.RIGHT, lambda x: FNot(*x)),
            (pp.Literal("&").suppress(), 2, pp.opAssoc.LEFT, lambda x: FAnd(*x)),
            (pp.Literal("|").suppress(), 2, pp.opAssoc.LEFT, lambda x: FOr(*x)),
        ],
    )
    expr = pp.OneOrMore(expr)
    return expr.setParseAction(lambda x: FAnd(x) if len(x) != 1 else x)


bnf = _make()


class TFilter(Protocol):
    pattern: str

    def __call__(self, f: flow.Flow) -> bool: ...  # pragma: no cover


def parse(s: str) -> TFilter:
    """
    Parse a filter expression and return the compiled filter function.
    If the filter syntax is invalid, `ValueError` is raised.
    """
    if not s:
        raise ValueError("Empty filter expression")
    try:
        flt = bnf.parseString(s, parseAll=True)[0]
        flt.pattern = s
        return flt
    except (pp.ParseException, ValueError) as e:
        raise ValueError(f"Invalid filter expression: {s!r}") from e


def match(flt: str | TFilter, flow: flow.Flow) -> bool:
    """
    Matches a flow against a compiled filter expression.
    Returns True if matched, False if not.

    If flt is a string, it will be compiled as a filter expression.
    If the expression is invalid, ValueError is raised.
    """
    if isinstance(flt, str):
        flt = parse(flt)
    if flt:
        return flt(flow)
    return True


match_all: TFilter = parse("~all")
"""A filter function that matches all flows"""


help = []
for a in filter_unary:
    help.append((f"~{a.code}", a.help))
for b in filter_rex:
    help.append((f"~{b.code} regex", b.help))
for c in filter_int:
    help.append((f"~{c.code} int", c.help))
help.sort()
help.extend(
    [
        ("!", "unary not"),
        ("&", "and"),
        ("|", "or"),
        ("(...)", "grouping"),
    ]
)
