import operator, string, random, mmap, os, time
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


def actions_log(lst):
    ret = []
    for i in lst:
        if i[1] == "inject":
            ret.append(
                [i[0], i[1], repr(i[2])]
            )
        else:
            ret.append(i)
    return ret


def ready_actions(length, lst):
    ret = []
    for i in lst:
        itms = list(i)
        if i[0] == "r":
            itms[0] = random.randrange(length)
        elif i[0] == "a":
            itms[0] = length+1
        ret.append(tuple(itms))
    ret.sort()
    return ret


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


#v_integer = pp.Regex(r"[+-]?\d+")\
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

    def __eq__(self, other):
        return self[:] == other

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


class _Value:
    def __init__(self, val):
        self.val = val.decode("string_escape")

    def get_generator(self, settings):
        return LiteralGenerator(self.val)

    def __repr__(self):
        return self.val


class ValueLiteral(_Value):
    @classmethod
    def expr(klass):
        e = v_literal.copy()
        return e.setParseAction(lambda x: klass(*x))


class ValueNakedLiteral(_Value):
    @classmethod
    def expr(klass):
        e = v_naked_literal.copy()
        return e.setParseAction(lambda x: klass(*x))


class ValueGenerate:
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

    def __str__(self):
        return "@%s%s,%s"%(self.usize, self.unit, self.datatype)


class ValueFile:
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

    def __str__(self):
        return "<%s"%(self.path)


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


class ShortcutContentType:
    def __init__(self, value):
        self.value = value

    def accept(self, settings, r):
        r.headers.append(
            (
                LiteralGenerator("Content-Type"),
                self.value.get_generator(settings)
            )
        )

    @classmethod
    def expr(klass):
        e = pp.Literal("c").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))



class ShortcutLocation:
    def __init__(self, value):
        self.value = value

    def accept(self, settings, r):
        r.headers.append(
            (
                LiteralGenerator("Location"),
                self.value.get_generator(settings)
            )
        )

    @classmethod
    def expr(klass):
        e = pp.Literal("l").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))


class Body:
    def __init__(self, value):
        self.value = value

    def accept(self, settings, r):
        r.body = self.value.get_generator(settings)

    @classmethod
    def expr(klass):
        e = pp.Literal("b").suppress()
        e = e + Value
        return e.setParseAction(lambda x: klass(*x))


class Raw:
    def accept(self, settings, r):
        r.raw = True

    @classmethod
    def expr(klass):
        e = pp.Literal("r").suppress()
        return e.setParseAction(lambda x: klass(*x))


class Path:
    def __init__(self, value):
        if isinstance(value, basestring):
            value = ValueLiteral(value)
        self.value = value

    def accept(self, settings, r):
        r.path = self.value.get_generator(settings)

    @classmethod
    def expr(klass):
        e = NakedValue.copy()
        return e.setParseAction(lambda x: klass(*x))



class Method:
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

    def accept(self, settings, r):
        r.method = self.value.get_generator(settings)

    @classmethod
    def expr(klass):
        parts = [pp.CaselessLiteral(i) for i in klass.methods]
        m = pp.MatchFirst(parts)
        spec = m | Value.copy()
        spec = spec.setParseAction(lambda x: klass(*x))
        return spec


class PauseAt:
    def __init__(self, offset, seconds):
        self.offset, self.seconds = offset, seconds

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

    def accept(self, settings, r):
        r.actions.append((self.offset, "pause", self.seconds))


class DisconnectAt:
    def __init__(self, value):
        self.value = value

    def accept(self, settings, r):
        r.actions.append((self.value, "disconnect"))

    @classmethod
    def expr(klass):
        e = pp.Literal("d").suppress()
        e += Offset
        return e.setParseAction(lambda x: klass(*x))


class InjectAt:
    def __init__(self, offset, value):
        self.offset, self.value = offset, value

    @classmethod
    def expr(klass):
        e = pp.Literal("i").suppress()
        e += Offset
        e += pp.Literal(",").suppress()
        e += Value
        return e.setParseAction(lambda x: klass(*x))

    def accept(self, settings, r):
        r.actions.append(
            (
                self.offset,
                "inject",
                self.value.get_generator(settings)
            )
        )


class Header:
    def __init__(self, key, value):
        self.key, self.value = key, value

    def accept(self, settings, r):
        r.headers.append(
            (
                self.key.get_generator(settings),
                self.value.get_generator(settings)
            )
        )

    @classmethod
    def expr(klass):
        e = pp.Literal("h").suppress()
        e += Value
        e += pp.Literal("=").suppress()
        e += Value
        return e.setParseAction(lambda x: klass(*x))


class Code:
    def __init__(self, code, msg=None):
        self.code, self.msg = code, msg
        if msg is None:
            self.msg = ValueLiteral(http_status.RESPONSES.get(self.code, "Unknown code"))

    def accept(self, settings, r):
        r.code = self.code
        r.msg = self.msg.get_generator(settings)

    @classmethod
    def expr(klass):
        e = v_integer
        e = e + pp.Optional(
            Value
        )
        return e.setParseAction(lambda x: klass(*x))



class Message:
    version = "HTTP/1.1"
    def __init__(self):
        self.body = LiteralGenerator("")
        self.headers = []
        self.actions = []
        self.raw = False

    def length(self):
        """
            Calculate the length of the base message without any applied actions.
        """
        l = sum(len(x) for x in self.preamble())
        l += 2
        for i in self.headers:
            l += len(i[0]) + len(i[1])
            l += 4
        l += 2
        l += len(self.body)
        return l

    def preview_safe(self):
        """
            Modify this message to be safe for previews. Returns a list of elided actions.
        """
        pauses = [i for i in self.actions if i[1] == "pause"]
        self.actions = [i for i in self.actions if i[1] != "pause"]
        return pauses

    def effective_length(self, actions):
        """
            Calculate the length of the base message with all applied actions.
        """
        # Order matters here, and must match the order of application in
        # write_values.
        l = self.length()
        for i in reversed(actions):
            if i[1] == "disconnect":
                return i[0]
            elif i[1] == "inject":
                l += len(i[2])
        return l

    def serve(self, fp, check, request_host):
        """
            fp: The file pointer to write to.

            check: A function called with the effective actions (after random
            values have been calculated). If it returns False service proceeds,
            otherwise the return is treated as an error message to be sent to
            the client, and service stops.

            request_host: If this a request, this is the connecting host. If
            None, we assume it's a response. Used to decide what standard
            modifications to make if raw is not set.

            Calling this function may modify the object.
        """
        started = time.time()
        if not self.raw:
            if self.body and not utils.get_header("Content-Length", self.headers):
                self.headers.append(
                    (
                        LiteralGenerator("Content-Length"),
                        LiteralGenerator(str(len(self.body))),
                    )
                )
            if request_host:
                if not utils.get_header("Host", self.headers):
                    self.headers.append(
                        (
                            LiteralGenerator("Host"),
                            LiteralGenerator(request_host)
                        )
                    )

            else:
                if not utils.get_header("Date", self.headers):
                    self.headers.append(
                        (
                            LiteralGenerator("Date"),
                            LiteralGenerator(formatdate(timeval=None, localtime=False, usegmt=True))
                        )
                    )

        hdrs = []
        for k, v in self.headers:
            hdrs.extend([
                k,
                ": ",
                v,
                "\r\n",
            ])
        vals = self.preamble()
        vals.append("\r\n")
        vals.extend(hdrs)
        vals.append("\r\n")
        if self.body:
            vals.append(self.body)
        vals.reverse()
        actions = ready_actions(self.length(), self.actions)
        actions.reverse()
        if check:
            ret = check(self, actions)
            if ret:
                err = PathodErrorResponse(ret)
                err.serve(fp)
                return dict(
                    disconnect = True,
                    actions = actions_log(actions),
                    error = ret
                )
        disconnect = write_values(fp, vals, actions[:])
        duration = time.time() - started
        ret = dict(
            disconnect = disconnect,
            started = started,
            duration = duration,
            actions = actions_log(actions),
        )
        for i in self.logattrs:
            v = getattr(self, i)
            # Careful not to log any VALUE specs without sanitizing them first. We truncate at 1k.
            if hasattr(v, "__len__"):
                v = v[:TRUNCATE]
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
        Raw
    )
    logattrs = ["code", "version"]
    def __init__(self):
        Message.__init__(self)
        self.code = 200
        self.msg = LiteralGenerator(http_status.RESPONSES[self.code])

    def preamble(self):
        return [self.version, " ", str(self.code), " ", self.msg]

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

    def __str__(self):
        parts = [
            "%s %s"%(self.code, self.msg[:])
        ]
        return "\n".join(parts)


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
    logattrs = ["method", "path"]
    def __init__(self):
        Message.__init__(self)
        self.method = None
        self.path = None

    def preamble(self):
        return [self.method, " ", self.path, " ", self.version]

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

    def __str__(self):
        parts = [
            "%s %s"%(self.method[:], self.path[:])
        ]
        return "\n".join(parts)


class CraftedRequest(Request):
    def __init__(self, settings, spec, tokens):
        Request.__init__(self)
        self.spec, self.tokens = spec, tokens
        for i in tokens:
            i.accept(settings, self)

    def serve(self, fp, check, host):
        d = Request.serve(self, fp, check, host)
        d["spec"] = self.spec
        return d


class CraftedResponse(Response):
    def __init__(self, settings, spec, tokens):
        Response.__init__(self)
        self.spec, self.tokens = spec, tokens
        for i in tokens:
            i.accept(settings, self)

    def serve(self, fp, check):
        d = Response.serve(self, fp, check, None)
        d["spec"] = self.spec
        return d


class PathodErrorResponse(Response):
    def __init__(self, msg, body=None):
        Response.__init__(self)
        self.code = 800
        self.msg = LiteralGenerator(msg)
        self.body = LiteralGenerator("pathod error: " + (body or msg))
        self.headers = [
            (
                LiteralGenerator("Content-Type"), LiteralGenerator("text/plain")
            ),
        ]

    def serve(self, fp, check=None):
        d = Response.serve(self, fp, check, None)
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
    if s.startswith(FILESTART):
        s = read_file(settings, s)
    try:
        return CraftedRequest(settings, s, Request.expr().parseString(s, parseAll=True))
    except pp.ParseException, v:
        raise ParseException(v.msg, v.line, v.col)
