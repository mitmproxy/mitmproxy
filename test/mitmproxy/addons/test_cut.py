
from mitmproxy.addons import cut
from mitmproxy.addons import view
from mitmproxy import exceptions
from mitmproxy.test import taddons
from mitmproxy.test import tflow
import pytest


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
    ]
    for t in tests:
        ret = cut.extract(t[0], tf)
        if ret != t[1]:
            raise AssertionError("Expected %s, got %s", t[1], ret)


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

        with pytest.raises(exceptions.CommandError):
            assert c.cut("moo") == [["svalue"]]

    v = view.View()
    c = cut.Cut()
    with taddons.context() as tctx:
        tctx.master.addons.add(v, c)
        v.add([tflow.ttcpflow()])
        assert c.cut("q.method|@all") == [[""]]
        assert c.cut("s.status|@all") == [[""]]
