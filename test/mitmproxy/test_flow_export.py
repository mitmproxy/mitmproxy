import json
from textwrap import dedent
import re

import netlib.tutils
from netlib.http import Headers
from mitmproxy import flow_export
from . import tutils


def clean_blanks(s):
    return re.sub(r"^(\s+)$", "", s, flags=re.MULTILINE)


def python_equals(testdata, text):
    """
        Compare two bits of Python code, disregarding non-significant differences
        like whitespace on blank lines and trailing space.
    """
    d = open(tutils.test_data.path(testdata)).read()
    assert clean_blanks(text).rstrip() == clean_blanks(d).rstrip()


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
        python_equals("test_flow_export/python_get.py", flow_export.python_code(flow))

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        python_equals("test_flow_export/python_post.py", flow_export.python_code(flow))

    def test_post_json(self):
        req_post.content = '{"name": "example", "email": "example@example.com"}'
        req_post.headers = Headers(content_type="application/json")
        flow = tutils.tflow(req=req_post)
        python_equals("test_flow_export/python_post_json.py", flow_export.python_code(flow))

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        python_equals("test_flow_export/python_patch.py", flow_export.python_code(flow))


class TestRawRequest():
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
            content-type: application/json\r
            host: address:22\r
            \r
            {"name": "example", "email": "example@example.com"}
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


class TestExportLocustCode():
    def test_get(self):
        flow = tutils.tflow(req=req_get)
        python_equals("test_flow_export/locust_get.py", flow_export.locust_code(flow))

    def test_post(self):
        req_post.content = '''content'''
        req_post.headers = ''
        flow = tutils.tflow(req=req_post)
        python_equals("test_flow_export/locust_post.py", flow_export.locust_code(flow))

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        python_equals("test_flow_export/locust_patch.py", flow_export.locust_code(flow))


class TestExportLocustTask():
    def test_get(self):
        flow = tutils.tflow(req=req_get)
        python_equals("test_flow_export/locust_task_get.py", flow_export.locust_task(flow))

    def test_post(self):
        flow = tutils.tflow(req=req_post)
        python_equals("test_flow_export/locust_task_post.py", flow_export.locust_task(flow))

    def test_patch(self):
        flow = tutils.tflow(req=req_patch)
        python_equals("test_flow_export/locust_task_patch.py", flow_export.locust_task(flow))


class TestIsJson():
    def test_empty(self):
        assert flow_export.is_json(None, None) is False

    def test_json_type(self):
        headers = Headers(content_type="application/json")
        assert flow_export.is_json(headers, "foobar") is False

    def test_valid(self):
        headers = Headers(content_type="application/foobar")
        j = flow_export.is_json(headers, '{"name": "example", "email": "example@example.com"}')
        assert j is False

    def test_valid(self):
        headers = Headers(content_type="application/json")
        j = flow_export.is_json(headers, '{"name": "example", "email": "example@example.com"}')
        assert isinstance(j, dict)
