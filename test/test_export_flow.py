import netlib.tutils
from libmproxy import flow_export
from . import tutils

req_get = netlib.tutils.treq(
    method='GET',
    content='',
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


def test_python_code():
    flow = tutils.tflow(req=req_get)
    result = ("""import requests\n\n"""
              """url = 'http://address/path'\n\n"""
              """headers = {\n"""
              """    'header': 'qvalue',\n"""
              """}\n\n"""
              """response = requests.request(\n"""
              """    method='GET',\n"""
              """    url=url,\n"""
              """    headers=headers,\n"""
              """)\n\n"""
              """print(response.text)""")
    assert flow_export.python_code(flow) == result

    flow = tutils.tflow(req=req_post)
    result = ("""import requests\n\n"""
              """url = 'http://address/path'\n\n"""
              """data = '''content'''\n\n"""
              """response = requests.request(\n"""
              """    method='POST',\n"""
              """    url=url,\n"""
              """    data=data,\n)\n\n"""
              """print(response.text)""")
    assert flow_export.python_code(flow) == result

    flow = tutils.tflow(req=req_patch)
    result = ("""import requests\n\n"""
              """url = 'http://address/path'\n\n"""
              """headers = {\n"""
              """    'header': 'qvalue',\n"""
              """}\n\n"""
              """params = {\n"""
              """    'query': 'param',\n"""
              """}\n\n"""
              """data = '''content'''\n\n"""
              """response = requests.request(\n"""
              """    method='PATCH',\n"""
              """    url=url,\n"""
              """    headers=headers,\n"""
              """    params=params,\n"""
              """    data=data,\n"""
              """)\n\n"""
              """print(response.text)""")
    assert flow_export.python_code(flow) == result


def test_raw_request():
    flow = tutils.tflow(req=req_get)
    result = ("""GET /path HTTP/1.1\r\n"""
              """header: qvalue\r\n"""
              """host: address:22\r\n\r\n"""
              """""")
    assert flow_export.raw_request(flow) == result

    flow = tutils.tflow(req=req_post)
    result = ("""POST /path HTTP/1.1\r\n"""
              """host: address:22\r\n\r\n"""
              """content""")
    assert flow_export.raw_request(flow) == result

    flow = tutils.tflow(req=req_patch)
    result = ("""PATCH /path?query=param HTTP/1.1\r\n"""
              """header: qvalue\r\n"""
              """host: address:22\r\n\r\n"""
              """content""")
    assert flow_export.raw_request(flow) == result
