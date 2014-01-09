import operator, string, random, mmap, os, time, copy
import abc
from email.utils import formatdate
import contrib.pyparsing as pp
from netlib import http_status, tcp, http_uastrings

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


def serve(msg, fp, settings, request_host=None):
    """
        fp: The file pointer to write to.

        request_host: If this a request, this is the connecting host. If
        None, we assume it's a response. Used to decide what standard
        modifications to make if raw is not set.

        Calling this function may modify the object.
    """
    msg = msg.resolve(settings, request_host)
    started = time.time()

    vals = msg.values(settings)
    vals.reverse()

    actions = msg.actions[:]
    actions.sort()
    actions.reverse()
    actions = [i.intermediate(settings) for i in actions]

    disconnect = write_values(fp, vals, actions[:])
    duration = time.time() - started
    ret = dict(
        disconnect = disconnect,
        started = started,
        duration = duration,
    )
    ret.update(msg.log(settings))
    return ret


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
        pp.Word("".join(i for i in pp.printables if i not in ",:\n@\'\""))
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
        self.fp = file(path, "rb")
        self.map = mmap.mmap(self.fp.fileno(), 0, access=mmap.ACCESS_READ)

    def __len__(self):
        return len(self.map)

    def __getitem__(self, x):
        return self.map.__getitem__(x)

    def __getslice__(self, a, b):
        return self.map.__getslice__(a, b)

    def __repr__(self):
        return "<%s"%self.path


class _Token(object):
    """
        A specification token. Tokens are immutable.
    """
    __metaclass__ = abc.ABCMeta
    @abc.abstractmethod
    def expr(klass): # pragma: no cover
        """
            A parse expression.
        """
        return None

    @abc.abstractmethod
    def spec(self): # pragma: no cover
        """
            A parseable specification for this token.
        """
        return None

    def resolve(self, msg, settings):
        """
            Resolves this token to ready it for transmission. This means that
            the calculated offsets of actions are fixed.
        """
        return self

    def __repr__(self):
        return self.spec()


class _ValueLiteral(_Token):
    def __init__(self, val):
        self.val = val.decode("string_escape")

    def get_generator(self, settings):
        return LiteralGenerator(self.val)

    def freeze(self, settings):
        return self


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


class ValueGenerate(_Token):
    def __init__(self, usize, unit, datatype):
        if not unit:
            unit = "b"
        self.usize, self.unit, self.datatype = usize, unit, datatype

    def bytes(self):
        return self.usize * utils.SIZE_UNITS[self.unit]

    def get_generator(self, settings):
        return RandomGenerator(self.datatype, self.bytes())

    def freeze(self, settings):
        g = self.get_generator(settings)
        return ValueLiteral(g[:].encode("string_escape"))

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


class ValueFile(_Token):
    def __init__(self, path):
        self.path = str(path)

    @classmethod
    def expr(klass):
        e = pp.Literal("<").suppress()
        e = e + v_naked_literal
        return e.setParseAction(lambda x: klass(*x))

    def freeze(self, settings):
        return self

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


class Raw(_Token):
    @classmethod
    def expr(klass):
        e = pp.Literal("r").suppress()
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "r"

    def freeze(self, settings):
        return self


class _Component(_Token):
    """
        A value component of the primary specification of an HTTP message.
    """
    @abc.abstractmethod
    def values(self, settings): # pragma: no cover
        """
           A sequence of value objects.
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


class Header(_Header):
    @classmethod
    def expr(klass):
        e = pp.Literal("h").suppress()
        e += Value
        e += pp.Literal("=").suppress()
        e += Value
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "h%s=%s"%(self.key.spec(), self.value.spec())

    def freeze(self, settings):
        return Header(self.key.freeze(settings), self.value.freeze(settings))


class ShortcutContentType(_Header):
    def __init__(self, value):
        _Header.__init__(self, ValueLiteral("Content-Type"), value)

    @classmethod
    def expr(klass):
        e = pp.Literal("c").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "c%s"%(self.value.spec())

    def freeze(self, settings):
        return ShortcutContentType(self.value.freeze(settings))


class ShortcutLocation(_Header):
    def __init__(self, value):
        _Header.__init__(self, ValueLiteral("Location"), value)

    @classmethod
    def expr(klass):
        e = pp.Literal("l").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "l%s"%(self.value.spec())

    def freeze(self, settings):
        return ShortcutLocation(self.value.freeze(settings))


class ShortcutUserAgent(_Header):
    def __init__(self, value):
        self.specvalue = value
        if isinstance(value, basestring):
            value = ValueLiteral(http_uastrings.get_by_shortcut(value)[2])
        _Header.__init__(self, ValueLiteral("User-Agent"), value)

    @classmethod
    def expr(klass):
        e = pp.Literal("u").suppress()
        u = reduce(operator.or_, [pp.Literal(i[1]) for i in http_uastrings.UASTRINGS])
        e += u | Value
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "u%s"%self.specvalue

    def freeze(self, settings):
        return ShortcutUserAgent(self.value.freeze(settings))



class Body(_Component):
    def __init__(self, value):
        self.value = value

    @classmethod
    def expr(klass):
        e = pp.Literal("b").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [
                self.value.get_generator(settings),
            ]

    def spec(self):
        return "b%s"%(self.value.spec())

    def freeze(self, settings):
        return Body(self.value.freeze(settings))


class Path(_Component):
    def __init__(self, value):
        if isinstance(value, basestring):
            value = ValueLiteral(value)
        self.value = value

    @classmethod
    def expr(klass):
        e = Value | NakedValue
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [
                self.value.get_generator(settings),
            ]

    def spec(self):
        return "%s"%(self.value.spec())

    def freeze(self, settings):
        return Path(self.value.freeze(settings))


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

    def spec(self):
        s = self.value.spec()
        if s[1:-1].lower() in self.methods:
            s = s[1:-1].lower()
        return "%s"%s

    def freeze(self, settings):
        return Method(self.value.freeze(settings))


class Code(_Component):
    def __init__(self, code):
        self.code = str(code)

    @classmethod
    def expr(klass):
        e = v_integer.copy()
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [LiteralGenerator(self.code)]

    def spec(self):
        return "%s"%(self.code)

    def freeze(self, settings):
        return Code(self.code)


class Reason(_Component):
    def __init__(self, value):
        self.value = value

    @classmethod
    def expr(klass):
        e = pp.Literal("m").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [self.value.get_generator(settings)]

    def spec(self):
        return "m%s"%(self.value.spec())

    def freeze(self, settings):
        return Reason(self.value.freeze(settings))


class _Action(_Token):
    """
        An action that operates on the raw data stream of the message. All
        actions have one thing in common: an offset that specifies where the
        action should take place.
    """
    def __init__(self, offset):
        self.offset = offset

    def resolve(self, msg, settings):
        """
            Resolves offset specifications to a numeric offset. Returns a copy
            of the action object.
        """
        c = copy.copy(self)
        l = msg.length(settings)
        if c.offset == "r":
            c.offset = random.randrange(l)
        elif c.offset == "a":
            c.offset = l + 1
        return c

    def __cmp__(self, other):
        return cmp(self.offset, other.offset)

    def __repr__(self):
        return self.spec()

    @abc.abstractmethod
    def spec(self): # pragma: no cover
        pass

    @abc.abstractmethod
    def intermediate(self): # pragma: no cover
        pass


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

    def freeze(self, settings):
        return self


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

    def freeze(self, settings):
        return self


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

    def freeze(self, settings):
        return InjectAt(self.offset, self.value.freeze(settings))


class _Message(object):
    __metaclass__ = abc.ABCMeta
    version = "HTTP/1.1"
    def __init__(self, tokens):
        self.tokens = tokens

    def _get_tokens(self, klass):
        return [i for i in self.tokens if isinstance(i, klass)]

    def _get_token(self, klass):
        l = self._get_tokens(klass)
        if l:
            return l[0]

    @property
    def raw(self):
        return bool(self._get_token(Raw))

    @property
    def actions(self):
        return self._get_tokens(_Action)

    @property
    def body(self):
        return self._get_token(Body)

    @property
    def headers(self):
        return self._get_tokens(_Header)

    def length(self, settings):
        """
            Calculate the length of the base message without any applied actions.
        """
        return sum(len(x) for x in self.values(settings))

    def preview_safe(self):
        """
            Return a copy of this message that issafe for previews.
        """
        tokens = [i for i in self.tokens if not isinstance(i, PauseAt)]
        return self.__class__(tokens)

    def maximum_length(self, settings):
        """
            Calculate the maximum length of the base message with all applied actions.
        """
        l = self.length(settings)
        for i in self.actions:
            if isinstance(i, InjectAt):
                l += len(i.value.get_generator(settings))
        return l

    def resolve(self, settings, request_host):
        tokens = self.tokens[:]
        if not self.raw:
            if not utils.get_header("Content-Length", self.headers):
                length = 0 if not self.body else len(self.body.value.get_generator(settings))
                tokens.append(
                    Header(
                        ValueLiteral("Content-Length"),
                        ValueLiteral(str(length)),
                    )
                )
            if request_host:
                if not utils.get_header("Host", self.headers):
                    tokens.append(
                        Header(
                            ValueLiteral("Host"),
                            ValueLiteral(request_host)
                        )
                    )
            else:
                if not utils.get_header("Date", self.headers):
                    tokens.append(
                        Header(
                            ValueLiteral("Date"),
                            ValueLiteral(formatdate(timeval=None, localtime=False, usegmt=True))
                        )
                    )
        intermediate = self.__class__(tokens)
        return self.__class__([i.resolve(intermediate, settings) for i in tokens])

    @abc.abstractmethod
    def preamble(self, settings): # pragma: no cover
        pass

    @abc.abstractmethod
    def expr(klass): # pragma: no cover
        pass

    def log(self, settings):
        """
            A dictionary that should be logged if this message is served.
        """
        ret = {}
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
        ret["spec"] = self.spec()
        return ret

    def values(self, settings):
        vals = self.preamble(settings)
        vals.append("\r\n")
        for h in self.headers:
            vals.extend(h.values(settings))
        vals.append("\r\n")
        if self.body:
            vals.append(self.body.value.get_generator(settings))
        return vals

    def freeze(self, settings, request_host=None):
        r = self.resolve(settings, request_host=None)
        return self.__class__([i.freeze(settings) for i in r.tokens])

    def __repr__(self):
        return self.spec()


Sep = pp.Optional(pp.Literal(":")).suppress()

class Response(_Message):
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
    @property
    def code(self):
        return self._get_token(Code)

    @property
    def reason(self):
        return self._get_token(Reason)

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

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


class Request(_Message):
    comps = (
        Body,
        Header,
        PauseAt,
        DisconnectAt,
        InjectAt,
        ShortcutContentType,
        ShortcutUserAgent,
        Raw
    )
    logattrs = ["method", "path", "body"]
    @property
    def method(self):
        return self._get_token(Method)

    @property
    def path(self):
        return self._get_token(Path)

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

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


class PathodErrorResponse(Response):
    pass


def make_error_response(reason, body=None):
    tokens = [
        Code("800"),
        Header(ValueLiteral("Content-Type"), ValueLiteral("text/plain")),
        Reason(ValueLiteral(reason)),
        Body(ValueLiteral("pathod error: " + (body or reason))),
    ]
    return PathodErrorResponse(tokens)

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
    return file(s, "rb").read()


def parse_response(settings, s):
    """
        May raise ParseException or FileAccessDenied
    """
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise ParseException("Spec must be valid ASCII.", 0, 0)
    if s.startswith(FILESTART):
        s = read_file(settings, s)
    try:
        return Response(Response.expr().parseString(s, parseAll=True))
    except pp.ParseException, v:
        raise ParseException(v.msg, v.line, v.col)


def parse_request(settings, s):
    """
        May raise ParseException or FileAccessDenied
    """
    try:
        s = s.decode("ascii")
    except UnicodeError:
        raise ParseException("Spec must be valid ASCII.", 0, 0)
    if s.startswith(FILESTART):
        s = read_file(settings, s)
    try:
        return Request(Request.expr().parseString(s, parseAll=True))
    except pp.ParseException, v:
        raise ParseException(v.msg, v.line, v.col)
