import operator, string, random, sys, time, mmap, os
import contrib.pyparsing as pp
import http, utils
import tornado.ioloop

TESTING = False

class ParseException(Exception): pass
class ServerError(Exception): pass


DATATYPES = dict(
    ascii_letters = string.ascii_letters,
    ascii_lowercase = string.ascii_lowercase,
    ascii_uppercase = string.ascii_uppercase,
    digits = string.digits,
    hexdigits = string.hexdigits,
    letters = string.letters,
    lowercase = string.lowercase,
    octdigits = string.octdigits,
    printable = string.printable,
    punctuation = string.punctuation,
    uppercase = string.uppercase,
    whitespace = string.whitespace,
    ascii = string.printable,
    bytes = "".join(chr(i) for i in range(256))
)


v_integer = pp.Regex(r"[+-]?\d+")\
    .setName("integer")\
    .setParseAction(lambda toks: int(toks[0]))

v_string = pp.MatchFirst(
    [
        pp.QuotedString("\"", escChar="\\", unquoteResults=True),
        pp.QuotedString("'", escChar="\\", unquoteResults=True),
    ]
)

v_literal = pp.MatchFirst(
    [
        v_string,
        pp.Word("".join(i for i in pp.printables if i not in ",:"))
    ]
)


class LiteralGenerator:
    def __init__(self, s):
        self.s = s

    def __eq__(self, other):
        return self[:] == other

    def __len__(self):
        return len(self.s)

    def __getitem__(self, x):
        return self.s.__getitem__(x)

    def __getslice__(self, a, b):
        return self.s.__getslice__(a, b)


class RandomGenerator:
    def __init__(self, chars, length):
        self.chars = chars
        self.length = length

    def __len__(self):
        return self.length

    def __getitem__(self, x):
        return random.choice(self.chars)

    def __getslice__(self, a, b):
        b = min(b, self.length)
        return "".join(random.choice(self.chars) for x in range(a, b))


class FileGenerator:
    def __init__(self, path):
        self.path = path
        self.fp = file(path, "r")
        self.map = mmap.mmap(self.fp.fileno(), 0, prot=mmap.PROT_READ)

    def __len__(self):
        return len(self.map)

    def __getitem__(self, x):
        return self.map.__getitem__(x)

    def __getslice__(self, a, b):
        return self.map.__getslice__(a, b)


class ValueLiteral:
    def __init__(self, val):
        self.val = val

    def get_generator(self, settings):
        return LiteralGenerator(self.val)

    @classmethod
    def expr(klass):
        e = v_literal.copy()
        return e.setParseAction(lambda x: klass(*x))

    def __str__(self):
        return self.val


class ValueGenerate:
    UNITS = dict(
        b = 1024**0,
        k = 1024**1,
        m = 1024**2,
        g = 1024**3,
        t = 1024**4,
    )
    def __init__(self, usize, unit, datatype):
        if not unit:
            unit = "b"
        self.usize, self.unit, self.datatype = usize, unit, datatype

    def bytes(self):
        return self.usize * self.UNITS[self.unit]

    def get_generator(self, settings):
        return RandomGenerator(DATATYPES[self.datatype], self.bytes())

    @classmethod
    def expr(klass):
        e = pp.Literal("!").suppress() + v_integer

        u = reduce(operator.or_, [pp.Literal(i) for i in klass.UNITS.keys()])
        e = e + pp.Optional(u, default=None)

        s = pp.Literal(":").suppress()
        s += reduce(operator.or_, [pp.Literal(i) for i in DATATYPES.keys()])
        e += pp.Optional(s, default="bytes")
        return e.setParseAction(lambda x: klass(*x))

    def __str__(self):
        return "!%s%s:%s"%(self.usize, self.unit, self.datatype)


class ValueFile:
    def __init__(self, path):
        self.path = path

    @classmethod
    def expr(klass):
        e = pp.Literal("<").suppress()
        e = e + v_literal
        return e.setParseAction(lambda x: klass(*x))

    def get_generator(self, settings):
        sd = settings.get("staticdir")
        if not sd:
            raise ServerError("No static directory specified.")
        path = os.path.join(sd, self.path)
        if not os.path.exists(path):
            raise ServerError("Static file does not exist: %s"%path)
        return FileGenerator(path)

    def __str__(self):
        return "<%s"%(self.path)


Value = pp.MatchFirst(
    [
        ValueGenerate.expr(),
        ValueFile.expr(),
        ValueLiteral.expr()
    ]
)


class Body:
    def __init__(self, value):
        self.value = value

    def mod_response(self, settings, r):
        r.body = self.value.get_generator(settings)

    @classmethod
    def expr(klass):
        e = pp.Literal("b:").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))


class _Pause:
    def __init__(self, value):
        self.value = value

    @classmethod
    def expr(klass):
        e = pp.Literal("p%s:"%klass.sub).suppress()
        e = e + pp.MatchFirst(
                    [
                        v_integer,
                        pp.Literal("forever")
                    ]
                )
        return e.setParseAction(lambda x: klass(*x))


class PauseBefore(_Pause):
    sub = "b"
    def mod_response(self, settings, r):
        r.pauses.append((0, self.value))


class PauseAfter(_Pause):
    sub = "a"
    def mod_response(self, settings, r):
        r.pauses.append((sys.maxint, self.value))


class PauseRandom(_Pause):
    sub = "r"
    def mod_response(self, settings, r):
        r.pauses.append(("random", self.value))



class _Disconnect:
    def __init__(self, value):
        self.value = value

    @classmethod
    def expr(klass):
        e = pp.Literal("d%s"%klass.sub)
        return e.setParseAction(klass)


class DisconnectBefore(_Disconnect):
    sub = "b"
    def mod_response(self, settings, r):
        r.pauses.append((0, self.value))


class DisconnectRandom(_Disconnect):
    sub = "r"
    def mod_response(self, settings, r):
        r.pauses.append(("random", self.value))


class Header:
    def __init__(self, key, value):
        self.key, self.value = key, value

    def mod_response(self, settings, r):
        r.headers.append(
            (
                self.key.get_generator(settings),
                self.value.get_generator(settings)
            )
        )

    @classmethod
    def expr(klass):
        e = pp.Literal("h:").suppress()
        e += Value
        e += pp.Literal(":").suppress()
        e += Value
        return e.setParseAction(lambda x: klass(*x))


class Code:
    def __init__(self, code, msg=None):
        self.code, self.msg = code, msg
        if msg is None:
            self.msg = ValueLiteral(http.RESPONSES.get(self.code, "Unknown code"))

    def mod_response(self, settings, r):
        r.code = self.code
        r.msg = self.msg.get_generator(settings)

    @classmethod
    def expr(klass):
        e = v_integer
        e = e + pp.Optional(
            pp.Literal(":").suppress() + Value
        )
        return e.setParseAction(lambda x: klass(*x))


BLOCKSIZE = 1024
class Response:
    comps = [
        Body,
        Header,
        PauseBefore,
        PauseAfter,
        PauseRandom,
        DisconnectBefore,
        DisconnectRandom,
    ]
    version = "HTTP/1.1"
    code = 200
    msg = LiteralGenerator(http.RESPONSES[code])
    body = LiteralGenerator("OK")
    def __init__(self, settings, tokens):
        self.tokens = tokens
        self.headers = []
        self.pauses = []
        for i in tokens:
            i.mod_response(settings, self)
        if self.body and not self.get_header("Content-Length"):
            self.headers.append(
                (
                    LiteralGenerator("Content-Length"),
                    LiteralGenerator(str(len(self.body))),
                )
            )

    def get_header(self, hdr):
        for k, v in self.headers:
            if k[:len(hdr)].lower() == hdr:
                return v
        return None

    @classmethod
    def expr(klass):
        parts = [i.expr() for i in klass.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                Code.expr(),
                pp.ZeroOrMore(pp.Literal(",").suppress() + atom)
            ]
        )
        return resp

    def length(self):
        l = len("%s %s "%(self.version, self.code))
        l += len(self.msg)
        l += 2
        for i in self.headers:
            l += len(i[0]) + len(i[1])
            l += 4
        l += 2
        l += len(self.body)
        return l

    def ready_randoms(self, l, lst):
        ret = []
        for k, v in lst:
            if k == "random":
                ret.append((random.randrange(l), v))
            else:
                ret.append((k, v))
        ret.sort()
        return ret

    def add_timeout(self, s, callback):
        if TESTING:
            callback()
        else:
            tornado.ioloop.IOLoop.instance().add_timeout(time.time() + s, callback)

    def write_values(self, fp, vals, pauses, disconnect, sofar=0, skip=0, blocksize=BLOCKSIZE):
        if disconnect == "before":
            fp.finish()
            return
        while vals:
            part = vals.pop()
            for i in range(skip, len(part), blocksize):
                d = part[i:i+blocksize]
                if pauses and pauses[-1][0] < (sofar + len(d)):
                    p = pauses.pop()
                    offset = p[0]-sofar
                    vals.append(part)
                    def pause_callback():
                        self.write_values(
                            fp, vals, pauses, disconnect,
                            sofar=sofar+offset,
                            skip=i+offset,
                            blocksize=blocksize
                        )
                    def flushed_callback():
                        # Data has been flushed, set the timeout.
                        self.add_timeout(p[1], pause_callback)
                    fp.write(d[:offset], callback=flushed_callback)
                    return
                fp.write(d)
                sofar += len(d)
            skip = 0
        fp.finish()

    def render(self, fp):
        hdrs = []
        for k, v in self.headers:
            hdrs.extend([
                k,
                ": ",
                v,
                "\r\n",
            ])
        vals = [
            "%s %s "%(self.version, self.code),
            self.msg,
            "\r\n",
        ]
        vals.extend(hdrs)
        vals.extend([
            "\r\n",
            self.body
        ])
        vals.reverse()
        pauses = self.ready_randoms(self.length(), self.pauses)
        pauses.reverse()
        return self.write_values(fp, vals, pauses, None)

    def __str__(self):
        parts = [
            "%s %s"%(self.code, self.msg[:])
        ]
        return "\n".join(parts)


class StubResponse:
    def __init__(self, code, body):
        self.code = code
        self.msg = LiteralGenerator(http.RESPONSES.get(code, "Unknown error"))
        self.body = LiteralGenerator(body)
        self.headers = [
            (
                LiteralGenerator("Content-Type"),
                LiteralGenerator("text/plain")
            ),
            (
                LiteralGenerator("Content-Length"),
                LiteralGenerator(str(len(self.body)))
            )
        ]


def parse(settings, s):
    try:
        return Response(settings, Response.expr().parseString(s, parseAll=True))
    except pp.ParseException, v:
        raise ParseException(v)
