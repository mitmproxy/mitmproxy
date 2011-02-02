
# Copyright (C) 2010  Aldo Cortesi
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
    The following operators are understood:

        ~q          Request
        ~s          Response
    
    Headers:

        Patterns are matched against "name: value" strings. Field names are
        all-lowercase.

        ~h rex      Header line in either request or response
        ~hq rex     Header in request
        ~hs rex     Header in response

        ~b rex      Expression in the body of either request or response
        ~bq rex     Expression in the body of request
        ~bq rex     Expression in the body of response
        ~t rex      Shortcut for content-type header.

        ~u rex      URL
        ~c CODE     Response code.
        rex         Equivalent to ~u rex 
"""
import re, sys
import contrib.pyparsing as pp


class _Token:
    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__,
        if hasattr(self, "expr"):
            print >> fp, "(%s)"%self.expr,
        print >> fp


class _Action(_Token):
    @classmethod
    def make(klass, s, loc, toks):
        return klass(*toks[1:])


class FReq(_Action):
    code = "q"
    help = "Match request"
    def __call__(self, conn):
        return not conn.is_response()


class FResp(_Action):
    code = "s"
    help = "Match response"
    def __call__(self, conn):
        return conn.is_response()
    

class _Rex(_Action):
    def __init__(self, expr):
        self.expr = expr
        try:
            self.re = re.compile(self.expr)
        except:
            raise ValueError, "Cannot compile expression."

def _check_content_type(expr, o):
    val = o.headers.get("content-type")
    if val and re.search(expr, val[0]):
        return True
    return False
    

class FContentType(_Rex):
    code = "t"
    help = "Content-type header"
    def __call__(self, o):
        if _check_content_type(self.expr, o):
            return True
        elif o.is_response() and _check_content_type(self.expr, o.request):
            return True
        else:
            return False


class FRequestContentType(_Rex):
    code = "tq"
    help = "Request Content-Type header"
    def __call__(self, o):
        if o.is_response():
            return _check_content_type(self.expr, o.request)
        else:
            return _check_content_type(self.expr, o)


class FResponseContentType(_Rex):
    code = "ts"
    help = "Request Content-Type header"
    def __call__(self, o):
        if o.is_response():
            return _check_content_type(self.expr, o)
        else:
            return False


class FHead(_Rex):
    code = "h"
    help = "Header"
    def __call__(self, o):
        val = o.headers.match_re(self.expr)
        if not val and o.is_response():
            val = o.request.headers.match_re(self.expr)
        return val
    

class FHeadRequest(_Rex):
    code = "hq"
    help = "Request header"
    def __call__(self, o):
        if o.is_response():
            h = o.request.headers
        else:
            h = o.headers
        return h.match_re(self.expr)


class FHeadResponse(_Rex):
    code = "hs"
    help = "Response header"
    def __call__(self, o):
        if not o.is_response():
            return False
        return o.headers.match_re(self.expr)


class FBod(_Rex):
    code = "b"
    help = "Body"
    def __call__(self, o):
        if o.content and re.search(self.expr, o.content):
            return True
        elif o.is_response() and o.request.content and re.search(self.expr, o.request.content):
            return True
        return False


class FBodRequest(_Rex):
    code = "bq"
    help = "Request body"
    def __call__(self, o):
        if o.is_response() and o.request.content and re.search(self.expr, o.request.content):
            return True
        elif not o.is_response() and o.content and re.search(self.expr, o.content):
            return True
        return False


class FBodResponse(_Rex):
    code = "bs"
    help = "Response body"
    def __call__(self, o):
        if not o.is_response():
            return False
        elif o.content and re.search(self.expr, o.content):
            return True
        return False
        

class FUrl(_Rex):
    code = "u"
    help = "URL"
    # FUrl is special, because it can be "naked".
    @classmethod
    def make(klass, s, loc, toks):
        if len(toks) > 1:
            toks = toks[1:]
        return klass(*toks)

    def __call__(self, o):
        if o.is_response():
            c = o.request
        else:
            c = o
        return re.search(self.expr, c.url())


class _Int(_Action):
    def __init__(self, num):
        self.num = int(num)


class FCode(_Int):
    code = "c"
    help = "HTTP response code"
    def __call__(self, o):
        if o.is_response():
            return o.code == self.num
        return False


class FAnd(_Token):
    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__
        for i in self.lst:
            i.dump(indent+1, fp)

    def __call__(self, o):
        return all([i(o) for i in self.lst])


class FOr(_Token):
    def __init__(self, lst):
        self.lst = lst

    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__
        for i in self.lst:
            i.dump(indent+1, fp)

    def __call__(self, o):
        return any([i(o) for i in self.lst])


class FNot(_Token):
    def __init__(self, itm):
        self.itm = itm[0]

    def dump(self, indent=0, fp=sys.stdout):
        print >> fp, "\t"*indent, self.__class__.__name__
        self.itm.dump(indent + 1, fp)

    def __call__(self, o):
        return not self.itm(o)

filt_unary = [
    FReq,
    FResp
]
filt_rex = [
    FHeadRequest,
    FHeadResponse,
    FHead,
    FBodRequest,
    FBodResponse,
    FBod,
    FUrl,
    FRequestContentType,
    FResponseContentType,
    FContentType,
]
filt_int = [
    FCode
]
def _make():
    # Order is important - multi-char expressions need to come before narrow
    # ones.
    parts = []
    for klass in filt_unary:
        f = pp.Literal("~%s"%klass.code)
        f.setParseAction(klass.make)
        parts.append(f)

    simplerex = "".join([c for c in pp.printables if c not in  "()~'\""])
    rex = pp.Word(simplerex) |\
          pp.QuotedString("\"", escChar='\\') |\
          pp.QuotedString("'", escChar='\\')
    for klass in filt_rex:
        f = pp.Literal("~%s"%klass.code) + rex.copy()
        f.setParseAction(klass.make)
        parts.append(f)

    for klass in filt_int:
        f = pp.Literal("~%s"%klass.code) + pp.Word(pp.nums)
        f.setParseAction(klass.make)
        parts.append(f)

    # A naked rex is a URL rex:
    f = rex.copy()
    f.setParseAction(FUrl.make)
    parts.append(f)

    atom = pp.MatchFirst(parts)
    expr = pp.operatorPrecedence(
                atom,
                [
                    (pp.Literal("!").suppress(), 1, pp.opAssoc.RIGHT, lambda x: FNot(*x)),
                    (pp.Literal("&").suppress(), 2, pp.opAssoc.LEFT, lambda x: FAnd(*x)),
                    (pp.Literal("|").suppress(), 2, pp.opAssoc.LEFT, lambda x: FOr(*x)),
                ]
           )
    expr = pp.OneOrMore(expr)
    return expr.setParseAction(lambda x: FAnd(x) if len(x) != 1 else x)
bnf = _make()


def parse(s):
    try:
        return bnf.parseString(s, parseAll=True)[0]
    except pp.ParseException:
        return None
    except ValueError, e:
        return None

