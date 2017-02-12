import json

from mitmproxy.test import tflow
import os
import shlex

from mitmproxy import options
from mitmproxy import contentviews
from mitmproxy import proxy
from mitmproxy.addons import script
from mitmproxy import master

from mitmproxy.test import tutils
from mitmproxy.net.http import Headers
from mitmproxy.net.http import cookies

from . import mastertest

example_dir = tutils.test_data.push("../examples")


class ScriptError(Exception):
    pass


class RaiseMaster(master.Master):
    def add_log(self, e, level):
        if level in ("warn", "error"):
            raise ScriptError(e)


def tscript(cmd, args=""):
    o = options.Options()
    cmd = example_dir.path(cmd) + " " + args
    m = RaiseMaster(o, proxy.DummyServer())
    sc = script.Script(cmd)
    m.addons.add(sc)
    return m, sc


class TestScripts(mastertest.MasterTest):
    def test_add_header(self):
        m, _ = tscript("simple/add_header.py")
        f = tflow.tflow(resp=tutils.tresp())
        m.response(f)
        assert f.response.headers["newheader"] == "foo"

    def test_custom_contentviews(self):
        m, sc = tscript("simple/custom_contentview.py")
        swapcase = contentviews.get("swapcase")
        _, fmt = swapcase(b"<html>Test!</html>")
        assert any(b'tEST!' in val[0][1] for val in fmt)

    def test_iframe_injector(self):
        with tutils.raises(ScriptError):
            tscript("simple/modify_body_inject_iframe.py")

        m, sc = tscript("simple/modify_body_inject_iframe.py", "http://example.org/evil_iframe")
        f = tflow.tflow(resp=tutils.tresp(content=b"<html><body>mitmproxy</body></html>"))
        m.response(f)
        content = f.response.content
        assert b'iframe' in content and b'evil_iframe' in content

    def test_modify_form(self):
        m, sc = tscript("simple/modify_form.py")

        form_header = Headers(content_type="application/x-www-form-urlencoded")
        f = tflow.tflow(req=tutils.treq(headers=form_header))
        m.request(f)

        assert f.request.urlencoded_form["mitmproxy"] == "rocks"

        f.request.headers["content-type"] = ""
        m.request(f)
        assert list(f.request.urlencoded_form.items()) == [("foo", "bar")]

    def test_modify_querystring(self):
        m, sc = tscript("simple/modify_querystring.py")
        f = tflow.tflow(req=tutils.treq(path="/search?q=term"))

        m.request(f)
        assert f.request.query["mitmproxy"] == "rocks"

        f.request.path = "/"
        m.request(f)
        assert f.request.query["mitmproxy"] == "rocks"

    def test_arguments(self):
        m, sc = tscript("simple/script_arguments.py", "mitmproxy rocks")
        f = tflow.tflow(resp=tutils.tresp(content=b"I <3 mitmproxy"))
        m.response(f)
        assert f.response.content == b"I <3 rocks"

    def test_redirect_requests(self):
        m, sc = tscript("simple/redirect_requests.py")
        f = tflow.tflow(req=tutils.treq(host="example.org"))
        m.request(f)
        assert f.request.host == "mitmproxy.org"

    def test_send_reply_from_proxy(self):
        m, sc = tscript("simple/send_reply_from_proxy.py")
        f = tflow.tflow(req=tutils.treq(host="example.com", port=80))
        m.request(f)
        assert f.response.content == b"Hello World"

    def test_dns_spoofing(self):
        m, sc = tscript("complex/dns_spoofing.py")
        original_host = "example.com"

        host_header = Headers(host=original_host)
        f = tflow.tflow(req=tutils.treq(headers=host_header, port=80))

        m.requestheaders(f)

        # Rewrite by reverse proxy mode
        f.request.scheme = "https"
        f.request.host = "mitmproxy.org"
        f.request.port = 443

        m.request(f)

        assert f.request.scheme == "http"
        assert f.request.host == original_host
        assert f.request.port == 80

        assert f.request.headers["Host"] == original_host


class TestHARDump:

    def flow(self, resp_content=b'message'):
        times = dict(
            timestamp_start=746203272,
            timestamp_end=746203272,
        )

        # Create a dummy flow for testing
        return tflow.tflow(
            req=tutils.treq(method=b'GET', **times),
            resp=tutils.tresp(content=resp_content, **times)
        )

    def test_no_file_arg(self):
        with tutils.raises(ScriptError):
            tscript("complex/har_dump.py")

    def test_simple(self):
        with tutils.tmpdir() as tdir:
            path = os.path.join(tdir, "somefile")

            m, sc = tscript("complex/har_dump.py", shlex.quote(path))
            m.addons.invoke(m, "response", self.flow())
            m.addons.remove(sc)

            with open(path, "r") as inp:
                har = json.load(inp)

        assert len(har["log"]["entries"]) == 1

    def test_base64(self):
        with tutils.tmpdir() as tdir:
            path = os.path.join(tdir, "somefile")

            m, sc = tscript("complex/har_dump.py", shlex.quote(path))
            m.addons.invoke(m, "response", self.flow(resp_content=b"foo" + b"\xFF" * 10))
            m.addons.remove(sc)

            with open(path, "r") as inp:
                har = json.load(inp)

        assert har["log"]["entries"][0]["response"]["content"]["encoding"] == "base64"

    def test_format_cookies(self):
        m, sc = tscript("complex/har_dump.py", "-")
        format_cookies = sc.ns.format_cookies

        CA = cookies.CookieAttrs

        f = format_cookies([("n", "v", CA([("k", "v")]))])[0]
        assert f['name'] == "n"
        assert f['value'] == "v"
        assert not f['httpOnly']
        assert not f['secure']

        f = format_cookies([("n", "v", CA([("httponly", None), ("secure", None)]))])[0]
        assert f['httpOnly']
        assert f['secure']

        f = format_cookies([("n", "v", CA([("expires", "Mon, 24-Aug-2037 00:00:00 GMT")]))])[0]
        assert f['expires']

    def test_binary(self):

        f = self.flow()
        f.request.method = "POST"
        f.request.headers["content-type"] = "application/x-www-form-urlencoded"
        f.request.content = b"foo=bar&baz=s%c3%bc%c3%9f"
        f.response.headers["random-junk"] = bytes(range(256))
        f.response.content = bytes(range(256))

        with tutils.tmpdir() as tdir:
            path = os.path.join(tdir, "somefile")

            m, sc = tscript("complex/har_dump.py", shlex.quote(path))
            m.addons.invoke(m, "response", f)
            m.addons.remove(sc)

            with open(path, "r") as inp:
                har = json.load(inp)

        assert len(har["log"]["entries"]) == 1
