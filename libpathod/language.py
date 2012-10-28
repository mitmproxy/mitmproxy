import operator, string, random, mmap, os, time, copy
import abc
from email.utils import formatdate
import contrib.pyparsing as pp
from netlib import http_status, tcp

import utils

BLOCKSIZE = 1024
TRUNCATE = 1024

class FileAccessDenied(Exception): pass


class ParseException(Exception):
    def __init__(self, msg, s, col):
        Exception.__init__(self)
        self.msg = msg
        self.s = s
        self.col = col

    def marked(self):
        return "%s\n%s"%(self.s, " "*(self.col-1) + "^")

    def __str__(self):
        return "%s at char %s"%(self.msg, self.col)


def send_chunk(fp, val, blocksize, start, end):
    """
        (start, end): Inclusive lower bound, exclusive upper bound.
    """
    for i in range(start, end, blocksize):
        fp.write(
            val[i:min(i+blocksize, end)]
        )
    return end-start


def write_values(fp, vals, actions, sofar=0, skip=0, blocksize=BLOCKSIZE):
    """
        vals: A list of values, which may be strings or Value objects.
        actions: A list of (offset, action, arg) tuples. Action may be "pause" or "disconnect".

        Both vals and actions are in reverse order, with the first items last.

        Return True if connection should disconnect.
    """
    sofar = 0
    try:
        while vals:
            v = vals.pop()
            offset = 0
            while actions and actions[-1][0] < (sofar + len(v)):
                a = actions.pop()
                offset += send_chunk(fp, v, blocksize, offset, a[0]-sofar-offset)
                if a[1] == "pause":
                    time.sleep(a[2])
                elif a[1] == "disconnect":
                    return True
                elif a[1] == "inject":
                    send_chunk(fp, a[2], blocksize, 0, len(a[2]))
            send_chunk(fp, v, blocksize, offset, len(v))
            sofar += len(v)
        # Remainders
        while actions:
            a = actions.pop()
            if a[1] == "pause":
                time.sleep(a[2])
            elif a[1] == "disconnect":
                return True
            elif a[1] == "inject":
                send_chunk(fp, a[2], blocksize, 0, len(a[2]))
    except tcp.NetLibDisconnect: # pragma: no cover
        return True


DATATYPES = dict(
    ascii_letters = string.ascii_letters,
    ascii_lowercase = string.ascii_lowercase,
    ascii_uppercase = string.ascii_uppercase,
    digits = string.digits,
    hexdigits = string.hexdigits,
    octdigits = string.octdigits,
    punctuation = string.punctuation,
    whitespace = string.whitespace,
    ascii = string.printable,
    bytes = "".join(chr(i) for i in range(256))
)


v_integer = pp.Regex(r"\d+")\
    .setName("integer")\
    .setParseAction(lambda toks: int(toks[0]))


v_literal = pp.MatchFirst(
    [
        pp.QuotedString("\"", escChar="\\", unquoteResults=True, multiline=True),
        pp.QuotedString("'", escChar="\\", unquoteResults=True, multiline=True),
    ]
)

v_naked_literal = pp.MatchFirst(
    [
        v_literal,
        pp.Word("".join(i for i in pp.printables if i not in ",:\n"))
    ]
)


class LiteralGenerator:
    def __init__(self, s):
        self.s = s

    def __len__(self):
        return len(self.s)

    def __getitem__(self, x):
        return self.s.__getitem__(x)

    def __getslice__(self, a, b):
        return self.s.__getslice__(a, b)

    def __repr__(self):
        return '"%s"'%self.s


class RandomGenerator:
    def __init__(self, dtype, length):
        self.dtype = dtype
        self.length = length

    def __len__(self):
        return self.length

    def __getitem__(self, x):
        return random.choice(DATATYPES[self.dtype])

    def __getslice__(self, a, b):
        b = min(b, self.length)
        chars = DATATYPES[self.dtype]
        return "".join(random.choice(chars) for x in range(a, b))

    def __repr__(self):
        return "%s random from %s"%(self.length, self.dtype)


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

    def __repr__(self):
        return "<%s"%self.path


class _Value(object):
    __metaclass__ = abc.ABCMeta
    def __repr__(self):
        return self.spec()

    @abc.abstractmethod
    def spec(self): # pragma: no cover
        return None

    @abc.abstractmethod
    def expr(self): # pragma: no cover
        return None


class _ValueLiteral(_Value):
    def __init__(self, val):
        self.val = val.decode("string_escape")

    def get_generator(self, settings):
        return LiteralGenerator(self.val)


class ValueLiteral(_ValueLiteral):
    @classmethod
    def expr(klass):
        e = v_literal.copy()
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return '"%s"'%self.val.encode("string_escape")


class ValueNakedLiteral(_ValueLiteral):
    @classmethod
    def expr(klass):
        e = v_naked_literal.copy()
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return self.val.encode("string_escape")


class ValueGenerate(_Value):
    def __init__(self, usize, unit, datatype):
        if not unit:
            unit = "b"
        self.usize, self.unit, self.datatype = usize, unit, datatype

    def bytes(self):
        return self.usize * utils.SIZE_UNITS[self.unit]

    def get_generator(self, settings):
        return RandomGenerator(self.datatype, self.bytes())

    @classmethod
    def expr(klass):
        e = pp.Literal("@").suppress() + v_integer

        u = reduce(operator.or_, [pp.Literal(i) for i in utils.SIZE_UNITS.keys()])
        e = e + pp.Optional(u, default=None)

        s = pp.Literal(",").suppress()
        s += reduce(operator.or_, [pp.Literal(i) for i in DATATYPES.keys()])
        e += pp.Optional(s, default="bytes")
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        s = "@%s"%self.usize
        if self.unit != "b":
            s += self.unit
        if self.datatype != "bytes":
            s += ",%s"%self.datatype
        return s


class ValueFile(_Value):
    def __init__(self, path):
        self.path = path

    @classmethod
    def expr(klass):
        e = pp.Literal("<").suppress()
        e = e + v_naked_literal
        return e.setParseAction(lambda x: klass(*x))

    def get_generator(self, settings):
        uf = settings.get("unconstrained_file_access")
        sd = settings.get("staticdir")
        if not sd:
            raise FileAccessDenied("File access disabled.")
        sd = os.path.normpath(os.path.abspath(sd))

        s = os.path.expanduser(self.path)
        s = os.path.normpath(os.path.abspath(os.path.join(sd, s)))
        if not uf and not s.startswith(sd):
            raise FileAccessDenied("File access outside of configured directory")
        if not os.path.isfile(s):
            raise FileAccessDenied("File not readable")
        return FileGenerator(s)

    def spec(self):
        return '<"%s"'%self.path.encode("string_escape")


Value = pp.MatchFirst(
    [
        ValueGenerate.expr(),
        ValueFile.expr(),
        ValueLiteral.expr()
    ]
)


NakedValue = pp.MatchFirst(
    [
        ValueGenerate.expr(),
        ValueFile.expr(),
        ValueLiteral.expr(),
        ValueNakedLiteral.expr(),
    ]
)


Offset = pp.MatchFirst(
        [
            v_integer,
            pp.Literal("r"),
            pp.Literal("a")
        ]
    )


class _Component(object):
    """
        A component of the specification of an HTTP message.
    """
    __metaclass__ = abc.ABCMeta
    @abc.abstractmethod
    def values(self, settings): # pragma: no cover
        """
           A sequence of value objects.
        """
        return None

    @abc.abstractmethod
    def expr(klass): # pragma: no cover
        """
            A parse expression.
        """
        return None

    @abc.abstractmethod
    def accept(self, r): # pragma: no cover
        """
            Notifies the component to register itself with message r.
        """
        return None

    def string(self, settings=None):
        """
            A string representation of the object.
        """
        return "".join(i[:] for i in self.values(settings or {}))


class _Header(_Component):
    def __init__(self, key, value):
        self.key, self.value = key, value

    def values(self, settings):
        return [
                self.key.get_generator(settings),
                ": ",
                self.value.get_generator(settings),
                "\r\n",
            ]

    def accept(self, r):
        r.headers.append(self)


class Header(_Header):
    @classmethod
    def expr(klass):
        e = pp.Literal("h").suppress()
        e += Value
        e += pp.Literal("=").suppress()
        e += Value
        return e.setParseAction(lambda x: klass(*x))


class ShortcutContentType(_Header):
    def __init__(self, value):
        _Header.__init__(self, ValueLiteral("Content-Type"), value)

    @classmethod
    def expr(klass):
        e = pp.Literal("c").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))


class ShortcutLocation(_Header):
    def __init__(self, value):
        _Header.__init__(self, ValueLiteral("Location"), value)

    @classmethod
    def expr(klass):
        e = pp.Literal("l").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))


class Body(_Component):
    def __init__(self, value):
        self.value = value

    def accept(self, r):
        r.body = self

    @classmethod
    def expr(klass):
        e = pp.Literal("b").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [
                self.value.get_generator(settings),
            ]


class Raw:
    def accept(self, r):
        r.raw = True

    @classmethod
    def expr(klass):
        e = pp.Literal("r").suppress()
        return e.setParseAction(lambda x: klass(*x))


class Path(_Component):
    def __init__(self, value):
        if isinstance(value, basestring):
            value = ValueLiteral(value)
        self.value = value

    def accept(self, r):
        r.path = self

    @classmethod
    def expr(klass):
        e = NakedValue.copy()
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [
                self.value.get_generator(settings),
            ]


class Method(_Component):
    methods = [
        "get",
        "head",
        "post",
        "put",
        "delete",
        "options",
        "trace",
        "connect",
    ]
    def __init__(self, value):
        # If it's a string, we were passed one of the methods, so we upper-case
        # it to be canonical. The user can specify a different case by using a
        # string value literal.
        if isinstance(value, basestring):
            value = ValueLiteral(value.upper())
        self.value = value

    def accept(self, r):
        r.method = self

    @classmethod
    def expr(klass):
        parts = [pp.CaselessLiteral(i) for i in klass.methods]
        m = pp.MatchFirst(parts)
        spec = m | Value.copy()
        spec = spec.setParseAction(lambda x: klass(*x))
        return spec

    def values(self, settings):
        return [
            self.value.get_generator(settings)
        ]


class _Action:
    """
        An action that operates on the raw data stream of the message. All
        actions have one thing in common: an offset that specifies where the
        action should take place.
    """
    def __init__(self, offset):
        self.offset = offset

    def resolve_offset(self, msg, settings, request_host):
        """
            Resolves offset specifications to a numeric offset. Returns a copy
            of the action object.
        """
        c = copy.copy(self)
        l = msg.length(settings, request_host)
        if c.offset == "r":
            c.offset = random.randrange(l)
        elif c.offset == "a":
            c.offset = l + 1
        return c

    def __cmp__(self, other):
        return cmp(self.offset, other.offset)

    def __repr__(self):
        return self.spec()

    def accept(self, r):
        r.actions.append(self)


class PauseAt(_Action):
    def __init__(self, offset, seconds):
        _Action.__init__(self, offset)
        self.seconds = seconds

    @classmethod
    def expr(klass):
        e = pp.Literal("p").suppress()
        e += Offset
        e += pp.Literal(",").suppress()
        e += pp.MatchFirst(
                    [
                        v_integer,
                        pp.Literal("f")
                    ]
                )
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "p%s,%s"%(self.offset, self.seconds)

    def intermediate(self, settings):
        return (self.offset, "pause", self.seconds)


class DisconnectAt(_Action):
    def __init__(self, offset):
        _Action.__init__(self, offset)

    @classmethod
    def expr(klass):
        e = pp.Literal("d").suppress()
        e += Offset
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "d%s"%self.offset

    def intermediate(self, settings):
        return (self.offset, "disconnect")


class InjectAt(_Action):
    def __init__(self, offset, value):
        _Action.__init__(self, offset)
        self.value = value

    @classmethod
    def expr(klass):
        e = pp.Literal("i").suppress()
        e += Offset
        e += pp.Literal(",").suppress()
        e += Value
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "i%s,%s"%(self.offset, self.value.spec())

    def intermediate(self, settings):
        return (
                self.offset,
                "inject",
                self.value.get_generator(settings)
            )


class Code(_Component):
    def __init__(self, code):
        self.code = str(code)

    def accept(self, r):
        r.code = self

    @classmethod
    def expr(klass):
        e = v_integer.copy()
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [LiteralGenerator(self.code)]


class Reason(_Component):
    def __init__(self, value):
        self.value = value

    def accept(self, r):
        r.reason = self

    @classmethod
    def expr(klass):
        e = pp.Literal("m").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [self.value.get_generator(settings)]


class Message:
    version = "HTTP/1.1"
    def __init__(self):
        self.body = None
        self.headers = []
        self.actions = []
        self.raw = False

    def length(self, settings, request_host):
        """
            Calculate the length of the base message without any applied actions.
        """
        l = sum(len(x) for x in self.preamble(settings))
        l += 2
        for h in self.headervals(settings, request_host):
            l += len(h)
        l += 2
        if self.body:
            l += len(self.body.value.get_generator(settings))
        return l

    def preview_safe(self):
        """
            Modify this message to be safe for previews. Returns a list of elided actions.
        """
        pauses = [i for i in self.actions if isinstance(i, PauseAt)]
        self.actions = [i for i in self.actions if not isinstance(i, PauseAt)]
        return pauses

    def maximum_length(self, settings, request_host):
        """
            Calculate the maximum length of the base message with all applied actions.
        """
        l = self.length(settings, request_host)
        for i in self.actions:
            if isinstance(i, InjectAt):
                l += len(i.value.get_generator(settings))
        return l

    def headervals(self, settings, request_host):
        hdrs = self.headers[:]
        if not self.raw:
            if self.body and not utils.get_header("Content-Length", self.headers):
                hdrs.append(
                    Header(
                        ValueLiteral("Content-Length"),
                        ValueLiteral(str(len(self.body.value.get_generator(settings)))),
                    )
                )
            if request_host:
                if not utils.get_header("Host", self.headers):
                    hdrs.append(
                        Header(
                            ValueLiteral("Host"),
                            ValueLiteral(request_host)
                        )
                    )

            else:
                if not utils.get_header("Date", self.headers):
                    hdrs.append(
                        Header(
                            ValueLiteral("Date"),
                            ValueLiteral(formatdate(timeval=None, localtime=False, usegmt=True))
                        )
                    )
        values = []
        for h in hdrs:
            values.extend(h.values(settings))
        return values

    def ready_actions(self, settings, request_host):
        actions = [i.resolve_offset(self, settings, request_host) for i in self.actions]
        actions.sort()
        actions.reverse()
        return [i.intermediate(settings) for i in actions]

    def serve(self, fp, settings, request_host):
        """
            fp: The file pointer to write to.

            request_host: If this a request, this is the connecting host. If
            None, we assume it's a response. Used to decide what standard
            modifications to make if raw is not set.

            Calling this function may modify the object.
        """
        started = time.time()

        hdrs = self.headervals(settings, request_host)

        vals = self.preamble(settings)
        vals.append("\r\n")
        vals.extend(hdrs)
        vals.append("\r\n")
        if self.body:
            vals.append(self.body.value.get_generator(settings))
        vals.reverse()
        actions = self.ready_actions(settings, request_host)

        disconnect = write_values(fp, vals, actions[:])
        duration = time.time() - started
        ret = dict(
            disconnect = disconnect,
            started = started,
            duration = duration,
        )
        for i in self.logattrs:
            v = getattr(self, i)
            # Careful not to log any VALUE specs without sanitizing them first. We truncate at 1k.
            if hasattr(v, "values"):
                v = [x[:TRUNCATE] for x in v.values(settings)]
                v = "".join(v).encode("string_escape")
            elif hasattr(v, "__len__"):
                v = v[:TRUNCATE]
                v = v.encode("string_escape")
            ret[i] = v
        return ret


Sep = pp.Optional(pp.Literal(":")).suppress()

class Response(Message):
    comps = (
        Body,
        Header,
        PauseAt,
        DisconnectAt,
        InjectAt,
        ShortcutContentType,
        ShortcutLocation,
        Raw,
        Reason
    )
    logattrs = ["code", "reason", "version", "body"]
    def __init__(self):
        Message.__init__(self)
        self.code = None
        self.reason = None

    def preamble(self, settings):
        l = [self.version, " "]
        l.extend(self.code.values(settings))
        l.append(" ")
        if self.reason:
            l.extend(self.reason.values(settings))
        else:
            l.append(LiteralGenerator(http_status.RESPONSES.get(int(self.code.code), "Unknown code")))
        return l

    @classmethod
    def expr(klass):
        parts = [i.expr() for i in klass.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                Code.expr(),
                pp.ZeroOrMore(Sep + atom)
            ]
        )
        return resp


class Request(Message):
    comps = (
        Body,
        Header,
        PauseAt,
        DisconnectAt,
        InjectAt,
        ShortcutContentType,
        Raw
    )
    logattrs = ["method", "path", "body"]
    def __init__(self):
        Message.__init__(self)
        self.method = None
        self.path = None

    def preamble(self, settings):
        v = self.method.values(settings)
        v.append(" ")
        v.extend(self.path.values(settings))
        v.append(" ")
        v.append(self.version)
        return v

    @classmethod
    def expr(klass):
        parts = [i.expr() for i in klass.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                Method.expr(),
                Sep,
                Path.expr(),
                pp.ZeroOrMore(Sep + atom)
            ]
        )
        return resp


class CraftedRequest(Request):
    def __init__(self, settings, spec, tokens):
        Request.__init__(self)
        self.spec, self.tokens = spec, tokens
        for i in tokens:
            i.accept(self)

    def serve(self, fp, settings, host):
        d = Request.serve(self, fp, settings, host)
        d["spec"] = self.spec
        return d


class CraftedResponse(Response):
    def __init__(self, settings, spec, tokens):
        Response.__init__(self)
        self.spec, self.tokens = spec, tokens
        for i in tokens:
            i.accept(self)

    def serve(self, fp, settings):
        d = Response.serve(self, fp, settings, None)
        d["spec"] = self.spec
        return d


class PathodErrorResponse(Response):
    def __init__(self, msg, body=None):
        Response.__init__(self)
        self.code = Code("800")
        self.msg = LiteralGenerator(msg)
        self.body = Body(ValueLiteral("pathod error: " + (body or msg)))
        self.headers = [
            Header(ValueLiteral("Content-Type"), ValueLiteral("text/plain")),
        ]

    def serve(self, fp, settings):
        d = Response.serve(self, fp, settings, None)
        d["internal"] = True
        return d


FILESTART = "+"
def read_file(settings, s):
    uf = settings.get("unconstrained_file_access")
    sd = settings.get("staticdir")
    if not sd:
        raise FileAccessDenied("File access disabled.")
    sd = os.path.normpath(os.path.abspath(sd))
    s = s[1:]
    s = os.path.expanduser(s)
    s = os.path.normpath(os.path.abspath(os.path.join(sd, s)))
    if not uf and not s.startswith(sd):
        raise FileAccessDenied("File access outside of configured directory")
    if not os.path.isfile(s):
        raise FileAccessDenied("File not readable")
    return file(s, "r").read()


def parse_response(settings, s):
    """
        May raise ParseException or FileAccessDenied
    """
    try:
        s.decode("ascii")
    except UnicodeError:
        raise ParseException("Spec must be valid ASCII.", 0, 0)
    if s.startswith(FILESTART):
        s = read_file(settings, s)
    try:
        return CraftedResponse(settings, s, Response.expr().parseString(s, parseAll=True))
    except pp.ParseException, v:
        raise ParseException(v.msg, v.line, v.col)


def parse_request(settings, s):
    """
        May raise ParseException or FileAccessDenied
    """
    try:
        s.decode("ascii")
    except UnicodeError:
        raise ParseException("Spec must be valid ASCII.", 0, 0)
    if s.startswith(FILESTART):
        s = read_file(settings, s)
    try:
        return CraftedRequest(settings, s, Request.expr().parseString(s, parseAll=True))
    except pp.ParseException, v:
        raise ParseException(v.msg, v.line, v.col)
