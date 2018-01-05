from mitmproxy.test import tflow
from mitmproxy.tools.console import common


def test_format_flow():
    f = tflow.tflow(resp=True)
    assert common.format_flow(f, True)
    assert common.format_flow(f, True, hostheader=True)
    assert common.format_flow(f, True, extended=True)
