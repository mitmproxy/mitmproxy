
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
        ["q.method", "GET"],
        ["q.scheme", "http"],
        ["q.host", "address"],
        ["q.port", "22"],
        ["q.path", "/path"],
        ["q.url", "http://address:22/path"],
        ["q.text", "content"],
        ["q.content", b"content"],
        ["q.raw_content", b"content"],
        ["q.header[header]", "qvalue"],

        ["s.status_code", "200"],
        ["s.reason", "OK"],
        ["s.text", "message"],
        ["s.content", b"message"],
        ["s.raw_content", b"message"],
        ["s.header[header-response]", "svalue"],

        ["cc.address.port", "22"],
        ["cc.address.host", "127.0.0.1"],
        ["cc.tls_version", "TLSv1.2"],
        ["cc.sni", "address"],
        ["cc.ssl_established", "false"],

        ["sc.address.port", "22"],
        ["sc.address.host", "address"],
        ["sc.ip_address.host", "192.168.0.1"],
        ["sc.tls_version", "TLSv1.2"],
        ["sc.sni", "address"],
        ["sc.ssl_established", "false"],
    ]
    for t in tests:
        ret = cut.extract(t[0], tf)
        if ret != t[1]:
            raise AssertionError("%s: Expected %s, got %s" % (t[0], t[1], ret))

    with open(tutils.test_data.path("mitmproxy/net/data/text_cert"), "rb") as f:
        d = f.read()
    c1 = certs.SSLCert.from_pem(d)
    tf.server_conn.cert = c1
    assert "CERTIFICATE" in cut.extract("sc.cert", tf)


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
            tctx.command(c.clip, "@all", "q.method")
            assert pc.called

        with mock.patch('pyperclip.copy') as pc:
            tctx.command(c.clip, "@all", "q.content")
            assert pc.called

        with mock.patch('pyperclip.copy') as pc:
            tctx.command(c.clip, "@all", "q.method,q.content")
            assert pc.called


def test_cut_save(tmpdir):
    f = str(tmpdir.join("path"))
    v = view.View()
    c = cut.Cut()
    with taddons.context() as tctx:
        tctx.master.addons.add(v, c)
        v.add([tflow.tflow(resp=True)])

        tctx.command(c.save, "@all", "q.method", f)
        assert qr(f) == b"GET"
        tctx.command(c.save, "@all", "q.content", f)
        assert qr(f) == b"content"
        tctx.command(c.save, "@all", "q.content", "+" + f)
        assert qr(f) == b"content\ncontent"

        v.add([tflow.tflow(resp=True)])
        tctx.command(c.save, "@all", "q.method", f)
        assert qr(f).splitlines() == [b"GET", b"GET"]
        tctx.command(c.save, "@all", "q.method,q.content", f)
        assert qr(f).splitlines() == [b"GET,content", b"GET,content"]


def test_cut():
    c = cut.Cut()
    with taddons.context():
        tflows = [tflow.tflow(resp=True)]
        assert c.cut(tflows, ["q.method"]) == [["GET"]]
        assert c.cut(tflows, ["q.scheme"]) == [["http"]]
        assert c.cut(tflows, ["q.host"]) == [["address"]]
        assert c.cut(tflows, ["q.port"]) == [["22"]]
        assert c.cut(tflows, ["q.path"]) == [["/path"]]
        assert c.cut(tflows, ["q.url"]) == [["http://address:22/path"]]
        assert c.cut(tflows, ["q.content"]) == [[b"content"]]
        assert c.cut(tflows, ["q.header[header]"]) == [["qvalue"]]
        assert c.cut(tflows, ["q.header[unknown]"]) == [[""]]

        assert c.cut(tflows, ["s.status_code"]) == [["200"]]
        assert c.cut(tflows, ["s.reason"]) == [["OK"]]
        assert c.cut(tflows, ["s.content"]) == [[b"message"]]
        assert c.cut(tflows, ["s.header[header-response]"]) == [["svalue"]]
        assert c.cut(tflows, ["moo"]) == [[""]]
        with pytest.raises(exceptions.CommandError):
            assert c.cut(tflows, ["__dict__"]) == [[""]]

    c = cut.Cut()
    with taddons.context():
        tflows = [tflow.ttcpflow()]
        assert c.cut(tflows, ["q.method"]) == [[""]]
        assert c.cut(tflows, ["s.status"]) == [[""]]
