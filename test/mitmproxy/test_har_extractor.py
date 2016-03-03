from . import tutils

from mitmproxy import script, flow
from examples import har_extractor


def test_start():
    fm = flow.FlowMaster(None, flow.State())
    ctx = script.ScriptContext(fm)
    tutils.raises(ValueError, har_extractor.start, ctx, [])
