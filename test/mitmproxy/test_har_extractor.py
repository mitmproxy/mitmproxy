import json
import netlib.tutils
from . import tutils

from mitmproxy import script, flow
from examples import har_extractor


trequest = netlib.tutils.treq(
    timestamp_start=746203272,
    timestamp_end=746203272,
)

tresponse = netlib.tutils.tresp(
    timestamp_start=746203272,
    timestamp_end=746203272,
)


def test_start():
    fm = flow.FlowMaster(None, flow.State())
    ctx = script.ScriptContext(fm)
    tutils.raises(ValueError, har_extractor.start, ctx, [])


def test_response():
    fm = flow.FlowMaster(None, flow.State())
    ctx = script.ScriptContext(fm)
    ctx.HARLog = har_extractor._HARLog([])
    ctx.seen_server = set()

    fl = tutils.tflow(req=trequest, resp=tresponse)
    har_extractor.response(ctx, fl)

    with open(tutils.test_data.path("data/har_extractor.har")) as fp:
        test_data = json.load(fp)
        assert json.loads(ctx.HARLog.json()) == test_data["test_response"]
