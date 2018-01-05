
from mitmproxy.addons import cut
from mitmproxy.addons import view
from mitmproxy import exceptions
from mitmproxy import certs
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils
import pytest
from unittest import mock


def test_extract():
    tf = tflow.tflow(resp=True)
    tests = [
        ["request.method", "GET"],
        ["request.scheme", "http"],
        ["request.host", "address"],
        ["request.http_version", "HTTP/1.1"],
        ["request.port", "22"],
        ["request.path", "/path"],
        ["request.url", "http://address:22/path"],
        ["request.text", "content"],
        ["request.content", b"content"],
        ["request.raw_content", b"content"],
        ["request.timestamp_start", "946681200"],
        ["request.timestamp_end", "946681201"],
        ["request.header[header]", "qvalue"],

        ["response.status_code", "200"],
        ["response.reason", "OK"],
        ["response.text", "message"],
        ["response.content", b"message"],
        ["response.raw_content", b"message"],
        ["response.header[header-response]", "svalue"],
        ["response.timestamp_start", "946681202"],
        ["response.timestamp_end", "946681203"],

        ["client_conn.address.port", "22"],
        ["client_conn.address.host", "127.0.0.1"],
        ["client_conn.tls_version", "TLSv1.2"],
        ["client_conn.sni", "address"],
        ["client_conn.ssl_established", "false"],

        ["server_conn.address.port", "22"],
        ["server_conn.address.host", "address"],
        ["server_conn.ip_address.host", "192.168.0.1"],
        ["server_conn.tls_version", "TLSv1.2"],
        ["server_conn.sni", "address"],
        ["server_conn.ssl_established", "false"],
    ]
    for spec, expected in tests:
        ret = cut.extract(spec, tf)
        assert spec and ret == expected

    with open(tutils.test_data.path("mitmproxy/net/data/text_cert"), "rb") as f:
        d = f.read()
    c1 = certs.SSLCert.from_pem(d)
    tf.server_conn.cert = c1
    assert "CERTIFICATE" in cut.extract("server_conn.cert", tf)


def test_headername():
    with pytest.raises(exceptions.CommandError):
        cut.headername("header[foo.")


def qr(f):
    with open(f, "rb") as fp:
        return fp.read()


def test_cut_clip():
    v = view.View()
    c = cut.Cut()
    with taddons.context() as tctx:
        tctx.master.addons.add(v, c)
        v.add([tflow.tflow(resp=True)])

        with mock.patch('pyperclip.copy') as pc:
            tctx.command(c.clip, "@all", "request.method")
            assert pc.called

        with mock.patch('pyperclip.copy') as pc:
            tctx.command(c.clip, "@all", "request.content")
            assert pc.called

        with mock.patch('pyperclip.copy') as pc:
            tctx.command(c.clip, "@all", "request.method,request.content")
            assert pc.called


def test_cut_save(tmpdir):
    f = str(tmpdir.join("path"))
    v = view.View()
    c = cut.Cut()
    with taddons.context() as tctx:
        tctx.master.addons.add(v, c)
        v.add([tflow.tflow(resp=True)])

        tctx.command(c.save, "@all", "request.method", f)
        assert qr(f) == b"GET"
        tctx.command(c.save, "@all", "request.content", f)
        assert qr(f) == b"content"
        tctx.command(c.save, "@all", "request.content", "+" + f)
        assert qr(f) == b"content\ncontent"

        v.add([tflow.tflow(resp=True)])
        tctx.command(c.save, "@all", "request.method", f)
        assert qr(f).splitlines() == [b"GET", b"GET"]
        tctx.command(c.save, "@all", "request.method,request.content", f)
        assert qr(f).splitlines() == [b"GET,content", b"GET,content"]


def test_cut():
    c = cut.Cut()
    with taddons.context():
        tflows = [tflow.tflow(resp=True)]
        assert c.cut(tflows, ["request.method"]) == [["GET"]]
        assert c.cut(tflows, ["request.scheme"]) == [["http"]]
        assert c.cut(tflows, ["request.host"]) == [["address"]]
        assert c.cut(tflows, ["request.port"]) == [["22"]]
        assert c.cut(tflows, ["request.path"]) == [["/path"]]
        assert c.cut(tflows, ["request.url"]) == [["http://address:22/path"]]
        assert c.cut(tflows, ["request.content"]) == [[b"content"]]
        assert c.cut(tflows, ["request.header[header]"]) == [["qvalue"]]
        assert c.cut(tflows, ["request.header[unknown]"]) == [[""]]

        assert c.cut(tflows, ["response.status_code"]) == [["200"]]
        assert c.cut(tflows, ["response.reason"]) == [["OK"]]
        assert c.cut(tflows, ["response.content"]) == [[b"message"]]
        assert c.cut(tflows, ["response.header[header-response]"]) == [["svalue"]]
        assert c.cut(tflows, ["moo"]) == [[""]]
        with pytest.raises(exceptions.CommandError):
            assert c.cut(tflows, ["__dict__"]) == [[""]]

    with taddons.context():
        tflows = [tflow.tflow(resp=False)]
        assert c.cut(tflows, ["response.reason"]) == [[""]]
        assert c.cut(tflows, ["response.header[key]"]) == [[""]]

    c = cut.Cut()
    with taddons.context():
        tflows = [tflow.ttcpflow()]
        assert c.cut(tflows, ["request.method"]) == [[""]]
        assert c.cut(tflows, ["response.status"]) == [[""]]
