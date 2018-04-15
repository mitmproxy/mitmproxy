import random
import string
import typing  # noqa

import pyparsing as pp

import mitmproxy.net.websockets
from mitmproxy.utils import strutils
from . import base, generators, actions, message

NESTED_LEADER = b"pathod!"


class WF(base.CaselessLiteral):
    TOK = "wf"


class OpCode(base.IntField):
    names: typing.Dict[str, int] = {
        "continue": mitmproxy.net.websockets.OPCODE.CONTINUE,
        "text": mitmproxy.net.websockets.OPCODE.TEXT,
        "binary": mitmproxy.net.websockets.OPCODE.BINARY,
        "close": mitmproxy.net.websockets.OPCODE.CLOSE,
        "ping": mitmproxy.net.websockets.OPCODE.PING,
        "pong": mitmproxy.net.websockets.OPCODE.PONG,
    }
    max = 15
    preamble = "c"


class Body(base.Value):
    preamble = "b"


class RawBody(base.Value):
    unique_name = "body"
    preamble = "r"


class Fin(base.Boolean):
    name = "fin"


class RSV1(base.Boolean):
    name = "rsv1"


class RSV2(base.Boolean):
    name = "rsv2"


class RSV3(base.Boolean):
    name = "rsv3"


class Mask(base.Boolean):
    name = "mask"


class Key(base.FixedLengthValue):
    preamble = "k"
    length = 4


class KeyNone(base.CaselessLiteral):
    unique_name = "key"
    TOK = "knone"


class Length(base.Integer):
    bounds = (0, 1 << 64)
    preamble = "l"


class Times(base.Integer):
    preamble = "x"


COMPONENTS = [
    OpCode,
    Length,
    # Bit flags
    Fin,
    RSV1,
    RSV2,
    RSV3,
    Mask,
    actions.PauseAt,
    actions.DisconnectAt,
    actions.InjectAt,
    KeyNone,
    Key,
    Times,
    Body,
    RawBody,
]


class WebsocketFrame(message.Message):
    components: typing.List[typing.Type[base._Component]] = COMPONENTS
    logattrs = ["body"]
    # Used for nested frames
    unique_name = "body"

    @property
    def actions(self):
        return self.toks(actions._Action)

    @property
    def body(self):
        return self.tok(Body)

    @property
    def rawbody(self):
        return self.tok(RawBody)

    @property
    def opcode(self):
        return self.tok(OpCode)

    @property
    def fin(self):
        return self.tok(Fin)

    @property
    def rsv1(self):
        return self.tok(RSV1)

    @property
    def rsv2(self):
        return self.tok(RSV2)

    @property
    def rsv3(self):
        return self.tok(RSV3)

    @property
    def mask(self):
        return self.tok(Mask)

    @property
    def key(self):
        return self.tok(Key)

    @property
    def knone(self):
        return self.tok(KeyNone)

    @property
    def times(self):
        return self.tok(Times)

    @property
    def toklength(self):
        return self.tok(Length)

    @classmethod
    def expr(cls):
        parts = [i.expr() for i in cls.components]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                WF.expr(),
                base.Sep,
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(cls)
        return resp

    @property
    def nested_frame(self):
        return self.tok(NestedFrame)

    def resolve(self, settings, msg=None):
        tokens = self.tokens[:]
        if not self.mask and settings.is_client:
            tokens.append(
                Mask(True)
            )
        if not self.knone and self.mask and self.mask.value and not self.key:
            allowed_chars = string.ascii_letters + string.digits
            k = ''.join([allowed_chars[random.randrange(0, len(allowed_chars))] for i in range(4)])
            tokens.append(
                Key(base.TokValueLiteral(k))
            )
        return self.__class__(
            [i.resolve(settings, self) for i in tokens]
        )

    def values(self, settings):
        if self.body:
            bodygen = self.body.value.get_generator(settings)
            length = len(self.body.value.get_generator(settings))
        elif self.rawbody:
            bodygen = self.rawbody.value.get_generator(settings)
            length = len(self.rawbody.value.get_generator(settings))
        elif self.nested_frame:
            bodygen = NESTED_LEADER + strutils.always_bytes(self.nested_frame.parsed.spec())
            length = len(bodygen)
        else:
            bodygen = None
            length = 0
        if self.toklength:
            length = int(self.toklength.value)
        frameparts = dict(
            payload_length=length
        )
        if self.mask and self.mask.value:
            frameparts["mask"] = True
        if self.knone:
            frameparts["masking_key"] = None
        elif self.key:
            key = self.key.values(settings)[0][:]
            frameparts["masking_key"] = key
        for i in ["opcode", "fin", "rsv1", "rsv2", "rsv3", "mask"]:
            v = getattr(self, i, None)
            if v is not None:
                frameparts[i] = v.value
        frame = mitmproxy.net.websockets.FrameHeader(**frameparts)
        vals = [bytes(frame)]
        if bodygen:
            if frame.masking_key and not self.rawbody:
                masker = mitmproxy.net.websockets.Masker(frame.masking_key)
                vals.append(
                    generators.TransformGenerator(
                        bodygen,
                        masker.mask
                    )
                )
            else:
                vals.append(bodygen)
        return vals

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])


class NestedFrame(message.NestedMessage):
    preamble = "f"
    nest_type = WebsocketFrame


class WebsocketClientFrame(WebsocketFrame):
    components = COMPONENTS + [NestedFrame]
