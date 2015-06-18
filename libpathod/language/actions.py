import abc
import copy
import random

import pyparsing as pp

from . import base


class _Action(base.Token):

    """
        An action that operates on the raw data stream of the message. All
        actions have one thing in common: an offset that specifies where the
        action should take place.
    """

    def __init__(self, offset):
        self.offset = offset

    def resolve(self, settings, msg):
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
    def spec(self):  # pragma: no cover
        pass

    @abc.abstractmethod
    def intermediate(self, settings):  # pragma: no cover
        pass


class PauseAt(_Action):
    unique_name = None

    def __init__(self, offset, seconds):
        _Action.__init__(self, offset)
        self.seconds = seconds

    @classmethod
    def expr(cls):
        e = pp.Literal("p").suppress()
        e += base.TokOffset
        e += pp.Literal(",").suppress()
        e += pp.MatchFirst(
            [
                base.v_integer,
                pp.Literal("f")
            ]
        )
        return e.setParseAction(lambda x: cls(*x))

    def spec(self):
        return "p%s,%s" % (self.offset, self.seconds)

    def intermediate(self, settings):
        return (self.offset, "pause", self.seconds)

    def freeze(self, settings_):
        return self


class DisconnectAt(_Action):

    def __init__(self, offset):
        _Action.__init__(self, offset)

    @classmethod
    def expr(cls):
        e = pp.Literal("d").suppress()
        e += base.TokOffset
        return e.setParseAction(lambda x: cls(*x))

    def spec(self):
        return "d%s" % self.offset

    def intermediate(self, settings):
        return (self.offset, "disconnect")

    def freeze(self, settings_):
        return self


class InjectAt(_Action):
    unique_name = None

    def __init__(self, offset, value):
        _Action.__init__(self, offset)
        self.value = value

    @classmethod
    def expr(cls):
        e = pp.Literal("i").suppress()
        e += base.TokOffset
        e += pp.Literal(",").suppress()
        e += base.TokValue
        return e.setParseAction(lambda x: cls(*x))

    def spec(self):
        return "i%s,%s" % (self.offset, self.value.spec())

    def intermediate(self, settings):
        return (
            self.offset,
            "inject",
            self.value.get_generator(settings)
        )

    def freeze(self, settings):
        return InjectAt(self.offset, self.value.freeze(settings))
