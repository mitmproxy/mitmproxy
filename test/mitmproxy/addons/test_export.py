import pytest
import os

from mitmproxy import exceptions
from mitmproxy.addons import export  # heh
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from unittest import mock


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


@pytest.fixture
def tcp_flow():
    return tflow.ttcpflow()


class TestExportCurlCommand:
    def test_get(self, get_request):
        result = """curl -H 'header:qvalue' -H 'content-length:0' 'http://address:22/path?a=foo&a=bar&b=baz'"""
        assert export.curl_command(get_request) == result

    def test_post(self, post_request):
        result = "curl -H 'content-length:256' -X POST 'http://address:22/path' --data-binary '{}'".format(
            str(bytes(range(256)))[2:-1]
        )
        assert export.curl_command(post_request) == result

    def test_patch(self, patch_request):
        result = """curl -H 'header:qvalue' -H 'content-length:7' -X PATCH 'http://address:22/path?query=param' --data-binary 'content'"""
        assert export.curl_command(patch_request) == result

    def test_tcp(self, tcp_flow):
        with pytest.raises(exceptions.CommandError):
            export.curl_command(tcp_flow)


class TestRaw:
    def test_get(self, get_request):
        assert b"header: qvalue" in export.raw(get_request)

    def test_tcp(self, tcp_flow):
        with pytest.raises(exceptions.CommandError):
            export.raw(tcp_flow)


def qr(f):
    with open(f, "rb") as fp:
        return fp.read()


def test_export(tmpdir):
    f = str(tmpdir.join("path"))
    e = export.Export()
    with taddons.context():
        assert e.formats() == ["curl", "raw"]
        with pytest.raises(exceptions.CommandError):
            e.file("nonexistent", tflow.tflow(resp=True), f)

        e.file("raw", tflow.tflow(resp=True), f)
        assert qr(f)
        os.unlink(f)

        e.file("curl", tflow.tflow(resp=True), f)
        assert qr(f)
        os.unlink(f)


def test_clip(tmpdir):
    e = export.Export()
    with taddons.context():
        with pytest.raises(exceptions.CommandError):
            e.clip("nonexistent", tflow.tflow(resp=True))

        with mock.patch('pyperclip.copy') as pc:
            e.clip("raw", tflow.tflow(resp=True))
            assert pc.called

        with mock.patch('pyperclip.copy') as pc:
            e.clip("curl", tflow.tflow(resp=True))
            assert pc.called
