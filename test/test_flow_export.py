from textwrap import dedent

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


class TestExportCurlCommand():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = """curl -H 'header:qvalue' -H 'content-length:7' 'http://address/path'"""
        assert flow_export.curl_command(flow) == result

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        result = """curl -X POST 'http://address/path' --data-binary 'content'"""
        assert flow_export.curl_command(flow) == result

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = """curl -H 'header:qvalue' -H 'content-length:7' -X PATCH 'http://address/path?query=param' --data-binary 'content'"""
        assert flow_export.curl_command(flow) == result


class TestExportPythonCode():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = dedent("""
            import requests

            url = 'http://address/path'

            headers = {
                'header': 'qvalue',
                'content-length': '7',
            }

            response = requests.request(
                method='GET',
                url=url,
                headers=headers,
            )

            print(response.text)
        """).strip()
        assert flow_export.python_code(flow) == result

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        result = dedent("""
            import requests

            url = 'http://address/path'

            data = '''content'''

            response = requests.request(
                method='POST',
                url=url,
                data=data,
            )

            print(response.text)
        """).strip()
        assert flow_export.python_code(flow) == result

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = dedent("""
            import requests

            url = 'http://address/path'

            headers = {
                'header': 'qvalue',
                'content-length': '7',
            }

            params = {
                'query': 'param',
            }

            data = '''content'''

            response = requests.request(
                method='PATCH',
                url=url,
                headers=headers,
                params=params,
                data=data,
            )

            print(response.text)
        """).strip()
        assert flow_export.python_code(flow) == result


def TestRawRequest():

    def test_get(self):
        flow = tutils.tflow(req=req_get)
        result = dedent("""
            GET /path HTTP/1.1\r
            header: qvalue\r
            content-length: 7\r
            host: address:22\r
            \r
        """).strip(" ").lstrip()
        assert flow_export.raw_request(flow) == result

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        result = dedent("""
            POST /path HTTP/1.1\r
            host: address:22\r
            \r
            content
        """).strip()
        assert flow_export.raw_request(flow) == result

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        result = dedent("""
            PATCH /path?query=param HTTP/1.1\r
            header: qvalue\r
            content-length: 7\r
            host: address:22\r
            \r
            content
        """).strip()
        assert flow_export.raw_request(flow) == result
