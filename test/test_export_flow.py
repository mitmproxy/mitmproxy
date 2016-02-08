import netlib.tutils
from libmproxy import flow_export
from . import tutils

req_get = netlib.tutils.treq(
    method='GET',
    headers=None,
    content=None,
)

req_post = netlib.tutils.treq(
    method='POST',
    headers=None,
)


def test_request_simple():
    flow = tutils.tflow(req=req_get)
    assert flow_export.curl_command(flow)

    flow = tutils.tflow(req=req_post)
    assert flow_export.curl_command(flow)
