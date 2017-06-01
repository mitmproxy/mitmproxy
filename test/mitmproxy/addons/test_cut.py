
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
        ["cc.address.host", "address"],
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


def test_parse_cutspec():
    tests = [
        ("", None, True),
        ("req.method", ("@all", ["req.method"]), False),
        (
            "req.method,req.host",
            ("@all", ["req.method", "req.host"]),
            False
        ),
        (
            "req.method,req.host|~b foo",
            ("~b foo", ["req.method", "req.host"]),
            False
        ),
        (
            "req.method,req.host|~b foo | ~b bar",
            ("~b foo | ~b bar", ["req.method", "req.host"]),
            False
        ),
        (
            "req.method, req.host | ~b foo | ~b bar",
            ("~b foo | ~b bar", ["req.method", "req.host"]),
            False
        ),
    ]
    for cutspec, output, err in tests:
        try:
            assert cut.parse_cutspec(cutspec) == output
        except exceptions.CommandError:
            if not err:
                raise
        else:
            if err:
                raise AssertionError("Expected error.")


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
            tctx.command(c.clip, "q.method|@all")
            assert pc.called

        with mock.patch('pyperclip.copy') as pc:
            tctx.command(c.clip, "q.content|@all")
            assert pc.called

        with mock.patch('pyperclip.copy') as pc:
            tctx.command(c.clip, "q.method,q.content|@all")
            assert pc.called


def test_cut_file(tmpdir):
    f = str(tmpdir.join("path"))
    v = view.View()
    c = cut.Cut()
    with taddons.context() as tctx:
        tctx.master.addons.add(v, c)

        v.add([tflow.tflow(resp=True)])

        tctx.command(c.save, "q.method|@all", f)
        assert qr(f) == b"GET"
        tctx.command(c.save, "q.content|@all", f)
        assert qr(f) == b"content"
        tctx.command(c.save, "q.content|@all", "+" + f)
        assert qr(f) == b"content\ncontent"

        v.add([tflow.tflow(resp=True)])
        tctx.command(c.save, "q.method|@all", f)
        assert qr(f).splitlines() == [b"GET", b"GET"]
        tctx.command(c.save, "q.method,q.content|@all", f)
        assert qr(f).splitlines() == [b"GET,content", b"GET,content"]


def test_cut():
    v = view.View()
    c = cut.Cut()
    with taddons.context() as tctx:
        v.add([tflow.tflow(resp=True)])
        tctx.master.addons.add(v, c)
        assert c.cut("q.method|@all") == [["GET"]]
        assert c.cut("q.scheme|@all") == [["http"]]
        assert c.cut("q.host|@all") == [["address"]]
        assert c.cut("q.port|@all") == [["22"]]
        assert c.cut("q.path|@all") == [["/path"]]
        assert c.cut("q.url|@all") == [["http://address:22/path"]]
        assert c.cut("q.content|@all") == [[b"content"]]
        assert c.cut("q.header[header]|@all") == [["qvalue"]]
        assert c.cut("q.header[unknown]|@all") == [[""]]

        assert c.cut("s.status_code|@all") == [["200"]]
        assert c.cut("s.reason|@all") == [["OK"]]
        assert c.cut("s.content|@all") == [[b"message"]]
        assert c.cut("s.header[header-response]|@all") == [["svalue"]]
        assert c.cut("moo") == [[""]]
        with pytest.raises(exceptions.CommandError):
            assert c.cut("__dict__") == [[""]]

    v = view.View()
    c = cut.Cut()
    with taddons.context() as tctx:
        tctx.master.addons.add(v, c)
        v.add([tflow.ttcpflow()])
        assert c.cut("q.method|@all") == [[""]]
        assert c.cut("s.status|@all") == [[""]]
