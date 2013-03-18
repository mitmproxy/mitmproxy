import libmproxy.console.common as common
from libmproxy import utils, flow, encoding
import tutils


def test_format_flow():
    f = tutils.tflow_full()
    assert common.format_flow(f, True)
    assert common.format_flow(f, True, hostheader=True)
    assert common.format_flow(f, True, extended=True)
