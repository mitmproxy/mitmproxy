import netlib.tutils
from libmproxy import flow_export
from . import tutils

req_get = netlib.tutils.treq(
    method='GET',
    content=None,
)

req_post = netlib.tutils.treq(
    method='POST',
    headers=None,
)

req_patch = netlib.tutils.treq(
    method='PATCH',
    path=b"/path?query=param",
)


def test_curl_command():
    flow = tutils.tflow(req=req_get)
    result = """curl -H 'header:qvalue' 'http://address/path'"""
    assert flow_export.curl_command(flow) == result

    flow = tutils.tflow(req=req_post)
    result = """curl -X POST 'http://address/path' --data-binary 'content'"""
    assert flow_export.curl_command(flow) == result

    flow = tutils.tflow(req=req_patch)
    result = """curl -H 'header:qvalue' -X PATCH 'http://address/path?query=param' --data-binary 'content'"""
    assert flow_export.curl_command(flow) == result

