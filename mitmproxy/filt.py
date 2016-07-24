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
                        application/x-shockwave-flash
        ~h rex      Header line in either request or response
        ~hq rex     Header in request
        ~hs rex     Header in response

        ~b rex      Expression in the body of either request or response
        ~bq rex     Expression in the body of request
        ~bq rex     Expression in the body of response
        ~t rex      Shortcut for content-type header.

        ~d rex      Request domain
        ~m rex      Method
        ~u rex      URL
        ~c CODE     Response code.
        rex         Equivalent to ~u rex
"""
from __future__ import absolute_import, print_function, division

import re
import sys
import functools

from mitmproxy.models.http import HTTPFlow
from mitmproxy.models.tcp import TCPFlow
from mitmproxy.models.flow import Flow

from netlib import strutils

import pyparsing as pp
from typing import Callable


def only(*types):
    def decorator(fn):
        @functools.wraps(fn)
        def filter_types(self, flow):
            if isinstance(flow, types):
                return fn(self, flow)
            return False
        return filter_types
    return decorator


class _Token(object):

    def dump(self, indent=0, fp=sys.stdout):
        print("{spacing}{name}{expr}".format(
            spacing="\t" * indent,
            name=self.__class__.__name__,
            expr=getattr(self, "expr", "")
        ), file=fp)


class _Action(_Token):

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
        return f.marked


class FHTTP(_Action):
    code = "http"
    help = "Match HTTP flows"

    @only(HTTPFlow)
    def __call__(self, f):
        return True


class FTCP(_Action):
    code = "tcp"
    help = "Match TCP flows"

    @only(TCPFlow)
    def __call__(self, f):
        return True


class FReq(_Action):
    code = "q"
    help = "Match request with no response"

    @only(HTTPFlow)
    def __call__(self, f):
        if not f.response:
            return True


class FResp(_Action):
    code = "s"
    help = "Match response"

    @only(HTTPFlow)
    def __call__(self, f):
        return bool(f.response)


class _Rex(_Action):
    flags = 0
    is_binary = True

    def __init__(self, expr):
        self.expr = expr
        if self.is_binary:
            expr = strutils.escaped_str_to_bytes(expr)
        try:
            self.re = re.compile(expr, self.flags)
        except:
            raise ValueError("Cannot compile expression.")


def _check_content_type(rex, message):
    return any(
        name.lower() == b"content-type" and
        rex.search(value)
        for name, value in message.headers.fields
    )


class FAsset(_Action):
    code = "a"
    help = "Match asset in response: CSS, Javascript, Flash, images."
    ASSET_TYPES = [
        b"text/javascript",
        b"application/x-javascript",
        b"application/javascript",
        b"text/css",
        b"image/.*",
        b"application/x-shockwave-flash"
    ]
    ASSET_TYPES = [re.compile(x) for x in ASSET_TYPES]

    @only(HTTPFlow)
    def __call__(self, f):
        if f.response:
            for i in self.ASSET_TYPES:
                if _check_content_type(i, f.response):
                    return True
        return False


class FContentType(_Rex):
    code = "t"
    help = "Content-type header"

    @only(HTTPFlow)
    def __call__(self, f):
        if _check_content_type(self.re, f.request):
            return True
        elif f.response and _check_content_type(self.re, f.response):
            return True
        return False


class FContentTypeRequest(_Rex):
    code = "tq"
    help = "Request Content-Type header"

    @only(HTTPFlow)
    def __call__(self, f):
        return _check_content_type(self.re, f.request)


class FContentTypeResponse(_Rex):
    code = "ts"
    help = "Response Content-Type header"

    @only(HTTPFlow)
    def __call__(self, f):
        if f.response:
            return _check_content_type(self.re, f.response)
        return False


class FHead(_Rex):
    code = "h"
    help = "Header"
    flags = re.MULTILINE

    @only(HTTPFlow)
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

    @only(HTTPFlow)
    def __call__(self, f):
        if f.request and self.re.search(bytes(f.request.headers)):
            return True


class FHeadResponse(_Rex):
    code = "hs"
    help = "Response header"
    flags = re.MULTILINE

    @only(HTTPFlow)
    def __call__(self, f):
        if f.response and self.re.search(bytes(f.response.headers)):
            return True


class FBod(_Rex):
    code = "b"
    help = "Body"

    @only(HTTPFlow, TCPFlow)
    def __call__(self, f):
        if isinstance(f, HTTPFlow):
            if f.request and f.request.raw_content:
                if self.re.search(f.request.get_content(strict=False)):
                    return True
            if f.response and f.response.raw_content:
                if self.re.search(f.response.get_content(strict=False)):
                    return True
        elif isinstance(f, TCPFlow):
            for msg in f.messages:
                if self.re.search(msg.content):
                    return True
        return False


class FBodRequest(_Rex):
    code = "bq"
    help = "Request body"

    @only(HTTPFlow, TCPFlow)
    def __call__(self, f):
        if isinstance(f, HTTPFlow):
            if f.request and f.request.raw_content:
                if self.re.search(f.request.get_content(strict=False)):
                    return True
        elif isinstance(f, TCPFlow):
            for msg in f.messages:
                if msg.from_client and self.re.search(msg.content):
                    return True


class FBodResponse(_Rex):
    code = "bs"
    help = "Response body"

    @only(HTTPFlow, TCPFlow)
    def __call__(self, f):
        if isinstance(f, HTTPFlow):
            if f.response and f.response.raw_content:
                if self.re.search(f.response.get_content(strict=False)):
                    return True
        elif isinstance(f, TCPFlow):
            for msg in f.messages:
                if not msg.from_client and self.re.search(msg.content):
                    return True


class FMethod(_Rex):
    code = "m"
    help = "Method"
    flags = re.IGNORECASE

    @only(HTTPFlow)
    def __call__(self, f):
        return bool(self.re.search(f.request.data.method))


class FDomain(_Rex):
    code = "d"
    help = "Domain"
    flags = re.IGNORECASE

    @only(HTTPFlow)
    def __call__(self, f):
        return bool(self.re.search(f.request.data.host))


class FUrl(_Rex):
    code = "u"
    help = "URL"
    is_binary = False
    # FUrl is special, because it can be "naked".

    @classmethod
    def make(klass, s, loc, toks):
        if len(toks) > 1:
            toks = toks[1:]
        return klass(*toks)

    @only(HTTPFlow)
    def __call__(self, f):
        return self.re.search(f.request.url)


class FSrc(_Rex):
    code = "src"
    help = "Match source address"
    is_binary = False

    def __call__(self, f):
        return f.client_conn.address and self.re.search(repr(f.client_conn.address))


class FDst(_Rex):
    code = "dst"
    help = "Match destination address"
    is_binary = False

    def __call__(self, f):
        return f.server_conn.address and self.re.search(repr(f.server_conn.address))


class _Int(_Action):

    def __init__(self, num):
        self.num = int(num)


class FCode(_Int):
    code = "c"
    help = "HTTP response code"

    @only(HTTPFlow)
    def __call__(self, f):
        if f.response and f.response.status_code == self.num:
            return True


class FAnd(_Token):

    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        super(FAnd, self).dump(indent, fp)
        for i in self.lst:
            i.dump(indent + 1, fp)

    def __call__(self, f):
        return all(i(f) for i in self.lst)


class FOr(_Token):

    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        super(FOr, self).dump(indent, fp)
        for i in self.lst:
            i.dump(indent + 1, fp)

    def __call__(self, f):
        return any(i(f) for i in self.lst)


class FNot(_Token):

    def __init__(self, itm):
        self.itm = itm[0]

    def dump(self, indent=0, fp=sys.stdout):
        super(FNot, self).dump(indent, fp)
        self.itm.dump(indent + 1, fp)

    def __call__(self, f):
        return not self.itm(f)


filt_unary = [
    FAsset,
    FErr,
    FHTTP,
    FMarked,
    FReq,
    FResp,
    FTCP,
]
filt_rex = [
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
]
filt_int = [
    FCode
]


def _make():
    # Order is important - multi-char expressions need to come before narrow
    # ones.
    parts = []
    for klass in filt_unary:
        f = pp.Literal("~%s" % klass.code) + pp.WordEnd()
        f.setParseAction(klass.make)
        parts.append(f)

    simplerex = "".join(c for c in pp.printables if c not in "()~'\"")
    rex = pp.Word(simplerex) |\
        pp.QuotedString("\"", escChar='\\') |\
        pp.QuotedString("'", escChar='\\')
    for klass in filt_rex:
        f = pp.Literal("~%s" % klass.code) + pp.WordEnd() + rex.copy()
        f.setParseAction(klass.make)
        parts.append(f)

    for klass in filt_int:
        f = pp.Literal("~%s" % klass.code) + pp.WordEnd() + pp.Word(pp.nums)
        f.setParseAction(klass.make)
        parts.append(f)

    # A naked rex is a URL rex:
    f = rex.copy()
    f.setParseAction(FUrl.make)
    parts.append(f)

    atom = pp.MatchFirst(parts)
    expr = pp.operatorPrecedence(atom,
                                 [(pp.Literal("!").suppress(),
                                   1,
                                   pp.opAssoc.RIGHT,
                                   lambda x: FNot(*x)),
                                     (pp.Literal("&").suppress(),
                                      2,
                                      pp.opAssoc.LEFT,
                                      lambda x: FAnd(*x)),
                                     (pp.Literal("|").suppress(),
                                      2,
                                      pp.opAssoc.LEFT,
                                      lambda x: FOr(*x)),
                                  ])
    expr = pp.OneOrMore(expr)
    return expr.setParseAction(lambda x: FAnd(x) if len(x) != 1 else x)
bnf = _make()


TFilter = Callable[[Flow], bool]


def parse(s):
    # type: (str) -> TFilter
    try:
        filt = bnf.parseString(s, parseAll=True)[0]
        filt.pattern = s
        return filt
    except pp.ParseException:
        return None
    except ValueError:
        return None


help = []
for i in filt_unary:
    help.append(
        ("~%s" % i.code, i.help)
    )
for i in filt_rex:
    help.append(
        ("~%s regex" % i.code, i.help)
    )
for i in filt_int:
    help.append(
        ("~%s int" % i.code, i.help)
    )
help.sort()
help.extend(
    [
        ("!", "unary not"),
        ("&", "and"),
        ("|", "or"),
        ("(...)", "grouping"),
    ]
)
