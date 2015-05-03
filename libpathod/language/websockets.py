
import netlib.websockets
import pyparsing as pp
from . import base, generators, actions, message

"""
    wf:ctext:b'foo'
    wf:c15:r'foo'
    wf:fin:rsv1:rsv2:rsv3:mask
    wf:-fin:-rsv1:-rsv2:-rsv3:-mask
    wf:p234
    wf:m"mask"
"""


class WF(base.CaselessLiteral):
    TOK = "wf"


class OpCode(base.IntField):
    names = {
        "continue": netlib.websockets.OPCODE.CONTINUE,
        "text": netlib.websockets.OPCODE.TEXT,
        "binary": netlib.websockets.OPCODE.BINARY,
        "close": netlib.websockets.OPCODE.CLOSE,
        "ping": netlib.websockets.OPCODE.PING,
        "pong": netlib.websockets.OPCODE.PONG,
    }
    max = 15
    preamble = "c"


class Body(base.Value):
    preamble = "b"


class Raw(base.CaselessLiteral):
    TOK = "r"


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


class WebsocketFrame(message.Message):
    comps = (
        Body,

        OpCode,
        # Bit flags
        Fin,
        RSV1,
        RSV2,
        RSV3,
        Mask,
        actions.PauseAt,
        actions.DisconnectAt,
        actions.InjectAt,

        Raw,
    )
    logattrs = ["body"]
    @property
    def actions(self):
        return self.toks(actions._Action)

    @property
    def body(self):
        return self.tok(Body)

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

    @classmethod
    def expr(klass):
        parts = [i.expr() for i in klass.comps]
        atom = pp.MatchFirst(parts)
        resp = pp.And(
            [
                WF.expr(),
                base.Sep,
                pp.ZeroOrMore(base.Sep + atom)
            ]
        )
        resp = resp.setParseAction(klass)
        return resp

    def values(self, settings):
        vals = []
        if self.body:
            bodygen = self.body.value.get_generator(settings)
            length = len(self.body.value.get_generator(settings))
        else:
            bodygen = None
            length = 0
        frameparts = dict(
            mask = True,
            payload_length = length
        )
        for i in ["opcode", "fin", "rsv1", "rsv2", "rsv3", "mask"]:
            v = getattr(self, i, None)
            if v is not None:
                frameparts[i] = v.value
        frame = netlib.websockets.FrameHeader(**frameparts)
        vals = [frame.to_bytes()]
        if self.body:
            masker = netlib.websockets.Masker(frame.masking_key)
            vals.append(
                generators.TransformGenerator(
                    bodygen,
                    masker.mask
                )
            )
        return vals

    def resolve(self, settings, msg=None):
        return self.__class__(
            [i.resolve(settings, msg) for i in self.tokens]
        )

    def spec(self):
        return ":".join([i.spec() for i in self.tokens])
