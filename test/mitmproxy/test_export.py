import re

import pytest

from mitmproxy import export  # heh
from mitmproxy.net.http import Headers
from mitmproxy.test import tflow
from mitmproxy.test import tutils


def clean_blanks(s):
    return re.sub(r"^\s+", "", s, flags=re.MULTILINE)


def python_equals(testdata, text):
    """
        Compare two bits of Python code, disregarding non-significant differences
        like whitespace on blank lines and trailing space.
    """
    d = open(tutils.test_data.path(testdata)).read()
    assert clean_blanks(text).rstrip() == clean_blanks(d).rstrip()


@pytest.fixture
def get_request():
    return tflow.tflow(
        req=tutils.treq(
            method=b'GET',
            content=b'',
            path=b"/path?a=foo&a=bar&b=baz"
        )
    )


@pytest.fixture
def post_request():
    return tflow.tflow(
        req=tutils.treq(
            method=b'POST',
            headers=(),
            content=bytes(range(256))
        )
    )


@pytest.fixture
def patch_request():
    return tflow.tflow(
        req=tutils.treq(method=b'PATCH', path=b"/path?query=param")
    )


class TExport:
    def test_get(self, get_request):
        raise NotImplementedError()

    def test_post(self, post_request):
        raise NotImplementedError()

    def test_patch(self, patch_request):
        raise NotImplementedError()


class TestExportCurlCommand(TExport):
    def test_get(self, get_request):
        result = """curl -H 'header:qvalue' -H 'content-length:7' 'http://address:22/path?a=foo&a=bar&b=baz'"""
        assert export.curl_command(get_request) == result

    def test_post(self, post_request):
        result = "curl -X POST 'http://address:22/path' --data-binary '{}'".format(
            str(bytes(range(256)))[2:-1]
        )
        assert export.curl_command(post_request) == result

    def test_patch(self, patch_request):
        result = """curl -H 'header:qvalue' -H 'content-length:7' -X PATCH 'http://address:22/path?query=param' --data-binary 'content'"""
        assert export.curl_command(patch_request) == result


class TestExportPythonCode(TExport):
    def test_get(self, get_request):
        python_equals("mitmproxy/data/test_flow_export/python_get.py",
                      export.python_code(get_request))

    def test_post(self, post_request):
        python_equals("mitmproxy/data/test_flow_export/python_post.py",
                      export.python_code(post_request))

    def test_post_json(self, post_request):
        post_request.request.content = b'{"name": "example", "email": "example@example.com"}'
        post_request.request.headers = Headers(content_type="application/json")
        python_equals("mitmproxy/data/test_flow_export/python_post_json.py",
                      export.python_code(post_request))

    def test_patch(self, patch_request):
        python_equals("mitmproxy/data/test_flow_export/python_patch.py",
                      export.python_code(patch_request))


class TestExportLocustCode(TExport):
    def test_get(self, get_request):
        python_equals("mitmproxy/data/test_flow_export/locust_get.py",
                      export.locust_code(get_request))

    def test_post(self, post_request):
        post_request.request.content = b'content'
        post_request.request.headers.clear()
        python_equals("mitmproxy/data/test_flow_export/locust_post.py",
                      export.locust_code(post_request))

    def test_patch(self, patch_request):
        python_equals("mitmproxy/data/test_flow_export/locust_patch.py",
                      export.locust_code(patch_request))


class TestExportLocustTask(TExport):
    def test_get(self, get_request):
        python_equals("mitmproxy/data/test_flow_export/locust_task_get.py",
                      export.locust_task(get_request))

    def test_post(self, post_request):
        python_equals("mitmproxy/data/test_flow_export/locust_task_post.py",
                      export.locust_task(post_request))

    def test_patch(self, patch_request):
        python_equals("mitmproxy/data/test_flow_export/locust_task_patch.py",
                      export.locust_task(patch_request))


class TestURL:
    def test_url(self):
        flow = tflow.tflow()
        assert export.url(flow) == "http://address:22/path"
