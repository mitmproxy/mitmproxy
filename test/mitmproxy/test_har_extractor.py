import json
import netlib.tutils
from . import tutils

from examples import har_extractor


class Context(object):
    pass


trequest = netlib.tutils.treq(
    timestamp_start=746203272,
    timestamp_end=746203272,
)

tresponse = netlib.tutils.tresp(
    timestamp_start=746203272,
    timestamp_end=746203272,
)


def test_start():
    tutils.raises(ValueError, har_extractor.start, Context(), [])


def test_response():
    ctx = Context()
    ctx.HARLog = har_extractor._HARLog([])
    ctx.seen_server = set()

    fl = tutils.tflow(req=trequest, resp=tresponse)
    har_extractor.response(ctx, fl)

    with open(tutils.test_data.path("data/har_extractor.har")) as fp:
        test_data = json.load(fp)
        assert json.loads(ctx.HARLog.json()) == test_data["test_response"]
