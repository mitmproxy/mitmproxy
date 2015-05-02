
import netlib.websockets
import contrib.pyparsing as pp
from . import base, generators

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


class WebsocketFrame(base._Message):
    comps = (
        base.Body,
        base.PauseAt,
        base.DisconnectAt,
        base.InjectAt
    )
    logattrs = ["body"]

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
        frame = netlib.websockets.FrameHeader(
            mask = True,
            payload_length = length
        )
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
