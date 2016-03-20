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
from __future__ import absolute_import, print_function
import re
import sys
import pyparsing as pp


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


class FReq(_Action):
    code = "q"
    help = "Match request with no response"

    def __call__(self, f):
        if not f.response:
            return True


class FResp(_Action):
    code = "s"
    help = "Match response"

    def __call__(self, f):
        return True if f.response else False


class _Rex(_Action):
    flags = 0

    def __init__(self, expr):
        self.expr = expr
        try:
            self.re = re.compile(self.expr, self.flags)
        except:
            raise ValueError("Cannot compile expression.")


def _check_content_type(expr, o):
    val = o.headers.get("content-type")
    if val and re.search(expr, val):
        return True
    return False


class FAsset(_Action):
    code = "a"
    help = "Match asset in response: CSS, Javascript, Flash, images."
    ASSET_TYPES = [
        "text/javascript",
        "application/x-javascript",
        "application/javascript",
        "text/css",
        "image/.*",
        "application/x-shockwave-flash"
    ]

    def __call__(self, f):
        if f.response:
            for i in self.ASSET_TYPES:
                if _check_content_type(i, f.response):
                    return True
        return False


class FContentType(_Rex):
    code = "t"
    help = "Content-type header"

    def __call__(self, f):
        if _check_content_type(self.expr, f.request):
            return True
        elif f.response and _check_content_type(self.expr, f.response):
            return True
        return False


class FRequestContentType(_Rex):
    code = "tq"
    help = "Request Content-Type header"

    def __call__(self, f):
        return _check_content_type(self.expr, f.request)


class FResponseContentType(_Rex):
    code = "ts"
    help = "Response Content-Type header"

    def __call__(self, f):
        if f.response:
            return _check_content_type(self.expr, f.response)
        return False


class FHead(_Rex):
    code = "h"
    help = "Header"
    flags = re.MULTILINE

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

    def __call__(self, f):
        if f.request and self.re.search(bytes(f.request.headers)):
            return True


class FHeadResponse(_Rex):
    code = "hs"
    help = "Response header"
    flags = re.MULTILINE

    def __call__(self, f):
        if f.response and self.re.search(bytes(f.response.headers)):
            return True


class FBod(_Rex):
    code = "b"
    help = "Body"

    def __call__(self, f):
        if f.request and f.request.content:
            if self.re.search(f.request.get_decoded_content()):
                return True
        if f.response and f.response.content:
            if self.re.search(f.response.get_decoded_content()):
                return True
        return False


class FBodRequest(_Rex):
    code = "bq"
    help = "Request body"

    def __call__(self, f):
        if f.request and f.request.content:
            if self.re.search(f.request.get_decoded_content()):
                return True


class FBodResponse(_Rex):
    code = "bs"
    help = "Response body"

    def __call__(self, f):
        if f.response and f.response.content:
            if self.re.search(f.response.get_decoded_content()):
                return True


class FMethod(_Rex):
    code = "m"
    help = "Method"
    flags = re.IGNORECASE

    def __call__(self, f):
        return bool(self.re.search(f.request.method))


class FDomain(_Rex):
    code = "d"
    help = "Domain"
    flags = re.IGNORECASE

    def __call__(self, f):
        return bool(self.re.search(f.request.host))


class FUrl(_Rex):
    code = "u"
    help = "URL"
    # FUrl is special, because it can be "naked".

    @classmethod
    def make(klass, s, loc, toks):
        if len(toks) > 1:
            toks = toks[1:]
        return klass(*toks)

    def __call__(self, f):
        return self.re.search(f.request.url)


class FSrc(_Rex):
    code = "src"
    help = "Match source address"

    def __call__(self, f):
        return f.client_conn.address and self.re.search(repr(f.client_conn.address))


class FDst(_Rex):
    code = "dst"
    help = "Match destination address"

    def __call__(self, f):
        return f.server_conn.address and self.re.search(repr(f.server_conn.address))


class _Int(_Action):

    def __init__(self, num):
        self.num = int(num)


class FCode(_Int):
    code = "c"
    help = "HTTP response code"

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
    FReq,
    FResp,
    FAsset,
    FErr
]
filt_rex = [
    FHeadRequest,
    FHeadResponse,
    FHead,
    FBodRequest,
    FBodResponse,
    FBod,
    FMethod,
    FDomain,
    FUrl,
    FRequestContentType,
    FResponseContentType,
    FContentType,
    FSrc,
    FDst,
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


def parse(s):
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
