import operator
import os
import abc
import pyparsing as pp

from .. import utils
from . import generators, exceptions


Sep = pp.Optional(pp.Literal(":")).suppress()


v_integer = pp.Word(pp.nums)\
    .setName("integer")\
    .setParseAction(lambda toks: int(toks[0]))


v_literal = pp.MatchFirst(
    [
        pp.QuotedString(
            "\"",
            unquoteResults=True,
            multiline=True
        ),
        pp.QuotedString(
            "'",
            unquoteResults=True,
            multiline=True
        ),
    ]
)

v_naked_literal = pp.MatchFirst(
    [
        v_literal,
        pp.Word("".join(i for i in pp.printables if i not in ",:\n@\'\""))
    ]
)


class Token(object):
    """
        A token in the specification language. Tokens are immutable. The token
        classes have no meaning in and of themselves, and are combined into
        Components and Actions to build the language.
    """
    __metaclass__ = abc.ABCMeta

    @classmethod
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

    def resolve(self, settings, msg):
        """
            Resolves this token to ready it for transmission. This means that
            the calculated offsets of actions are fixed.

            settings: a language.Settings instance
            msg: The containing message
        """
        return self

    def __repr__(self):
        return self.spec()


class _TokValueLiteral(Token):
    def __init__(self, val):
        self.val = val.decode("string_escape")

    def get_generator(self, settings):
        return self.val

    def freeze(self, settings):
        return self


class TokValueLiteral(_TokValueLiteral):
    """
        A literal with Python-style string escaping
    """
    @classmethod
    def expr(klass):
        e = v_literal.copy()
        return e.setParseAction(klass.parseAction)

    @classmethod
    def parseAction(klass, x):
        v = klass(*x)
        return v

    def spec(self):
        inner = self.val.encode("string_escape")
        inner = inner.replace(r"\'", r"\x27")
        return "'" + inner + "'"


class TokValueNakedLiteral(_TokValueLiteral):
    @classmethod
    def expr(klass):
        e = v_naked_literal.copy()
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return self.val.encode("string_escape")


class TokValueGenerate(Token):
    def __init__(self, usize, unit, datatype):
        if not unit:
            unit = "b"
        self.usize, self.unit, self.datatype = usize, unit, datatype

    def bytes(self):
        return self.usize * utils.SIZE_UNITS[self.unit]

    def get_generator(self, settings):
        return generators.RandomGenerator(self.datatype, self.bytes())

    def freeze(self, settings):
        g = self.get_generator(settings)
        return TokValueLiteral(g[:].encode("string_escape"))

    @classmethod
    def expr(klass):
        e = pp.Literal("@").suppress() + v_integer

        u = reduce(
            operator.or_,
            [pp.Literal(i) for i in utils.SIZE_UNITS.keys()]
        ).leaveWhitespace()
        e = e + pp.Optional(u, default=None)

        s = pp.Literal(",").suppress()
        s += reduce(
            operator.or_,
            [pp.Literal(i) for i in generators.DATATYPES.keys()]
        )
        e += pp.Optional(s, default="bytes")
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        s = "@%s"%self.usize
        if self.unit != "b":
            s += self.unit
        if self.datatype != "bytes":
            s += ",%s"%self.datatype
        return s


class TokValueFile(Token):
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
        if not settings.staticdir:
            raise exceptions.FileAccessDenied("File access disabled.")
        s = os.path.expanduser(self.path)
        s = os.path.normpath(
            os.path.abspath(os.path.join(settings.staticdir, s))
        )
        uf = settings.unconstrained_file_access
        if not uf and not s.startswith(settings.staticdir):
            raise exceptions.FileAccessDenied(
                "File access outside of configured directory"
            )
        if not os.path.isfile(s):
            raise exceptions.FileAccessDenied("File not readable")
        return generators.FileGenerator(s)

    def spec(self):
        return "<'%s'"%self.path.encode("string_escape")


TokValue = pp.MatchFirst(
    [
        TokValueGenerate.expr(),
        TokValueFile.expr(),
        TokValueLiteral.expr()
    ]
)


TokNakedValue = pp.MatchFirst(
    [
        TokValueGenerate.expr(),
        TokValueFile.expr(),
        TokValueLiteral.expr(),
        TokValueNakedLiteral.expr(),
    ]
)


TokOffset = pp.MatchFirst(
    [
        v_integer,
        pp.Literal("r"),
        pp.Literal("a")
    ]
)


class _Component(Token):
    """
        A value component of the primary specification of an message.
        Components produce byte values desribe the bytes of the message.
    """
    def values(self, settings): # pragma: no cover
        """
           A sequence of values, which can either be strings or generators.
        """
        pass

    def string(self, settings=None):
        """
            A string representation of the object.
        """
        return "".join(i[:] for i in self.values(settings or {}))


class KeyValue(_Component):
    """
        A key/value pair.
        klass.preamble: leader
    """
    def __init__(self, key, value):
        self.key, self.value = key, value

    @classmethod
    def expr(klass):
        e = pp.Literal(klass.preamble).suppress()
        e += TokValue
        e += pp.Literal("=").suppress()
        e += TokValue
        return e.setParseAction(lambda x: klass(*x))

    def spec(self):
        return "%s%s=%s"%(self.preamble, self.key.spec(), self.value.spec())

    def freeze(self, settings):
        return self.__class__(
            self.key.freeze(settings), self.value.freeze(settings)
        )


class CaselessLiteral(_Component):
    """
        A caseless token that can take only one value.
    """
    def __init__(self, value):
        self.value = value

    @classmethod
    def expr(klass):
        spec = pp.CaselessLiteral(klass.TOK)
        spec = spec.setParseAction(lambda x: klass(*x))
        return spec

    def values(self, settings):
        return self.TOK

    def spec(self):
        return self.TOK

    def freeze(self, settings):
        return self


class OptionsOrValue(_Component):
    """
        Can be any of a specified set of options, or a value specifier.
    """
    preamble = ""
    options = []
    def __init__(self, value):
        # If it's a string, we were passed one of the options, so we lower-case
        # it to be canonical. The user can specify a different case by using a
        # string value literal.
        self.option_used = False
        if isinstance(value, basestring):
            for i in self.options:
                # Find the exact option value in a case-insensitive way
                if i.lower() == value.lower():
                    self.option_used = True
                    value = TokValueLiteral(i)
                    break
        self.value = value

    @classmethod
    def expr(klass):
        parts = [pp.CaselessLiteral(i) for i in klass.options]
        m = pp.MatchFirst(parts)
        spec = m | TokValue.copy()
        spec = spec.setParseAction(lambda x: klass(*x))
        if klass.preamble:
            spec = pp.Literal(klass.preamble).suppress() + spec
        return spec

    def values(self, settings):
        return [
            self.value.get_generator(settings)
        ]

    def spec(self):
        s = self.value.spec()
        if s[1:-1].lower() in self.options:
            s = s[1:-1].lower()
        return "%s%s"%(self.preamble, s)

    def freeze(self, settings):
        return self.__class__(self.value.freeze(settings))


class Integer(_Component):
    def __init__(self, value):
        self.value = str(value)

    @classmethod
    def expr(klass):
        e = v_integer.copy()
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return self.value

    def spec(self):
        return "%s"%(self.value)

    def freeze(self, settings):
        return self


class Value(_Component):
    """
        A value component lead by an optional preamble.
    """
    preamble = ""

    def __init__(self, value):
        self.value = value

    @classmethod
    def expr(klass):
        e = (TokValue | TokNakedValue)
        if klass.preamble:
            e = pp.Literal(klass.preamble).suppress() + e
        return e.setParseAction(lambda x: klass(*x))

    def values(self, settings):
        return [self.value.get_generator(settings)]

    def spec(self):
        return "%s%s"%(self.preamble, self.value.spec())

    def freeze(self, settings):
        return self.__class__(self.value.freeze(settings))


class Boolean(_Component):
    """
        A boolean flag.
            name  = true
            -name = false
    """
    name = ""

    def __init__(self, value):
        self.value = value

    @classmethod
    def expr(klass):
        e = pp.Optional(pp.Literal("-"), default=True)
        e += pp.Literal(klass.name).suppress()

        def parse(s, loc, toks):
            val = True
            if toks[0] == "-":
                val = False
            return klass(val)

        return e.setParseAction(parse)

    def spec(self):
        return "%s%s"%("-" if not self.value else "", self.name)


class IntField(_Component):
    """
        An integer field, where values can optionally specified by name.
    """
    names = {}
    max = 16
    preamble = ""

    def __init__(self, value):
        self.origvalue = value
        self.value = self.names.get(value, value)
        if self.value > self.max:
            raise exceptions.ParseException(
                "Value can't exceed %s"%self.max, 0, 0
            )

    @classmethod
    def expr(klass):
        parts = [pp.CaselessLiteral(i) for i in klass.names.keys()]
        m = pp.MatchFirst(parts)
        spec = m | v_integer.copy()
        spec = spec.setParseAction(lambda x: klass(*x))
        if klass.preamble:
            spec = pp.Literal(klass.preamble).suppress() + spec
        return spec

    def values(self, settings):
        return [str(self.value)]

    def spec(self):
        return "%s%s"%(self.preamble, self.origvalue)
