from mitmproxy import options
from mitmproxy import contentviews
from mitmproxy import proxy
from mitmproxy import master
from mitmproxy.addons import script

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy.net.http import Headers

from ..mitmproxy import tservers

example_dir = tutils.test_data.push("../examples")


class ScriptError(Exception):
    pass


class RaiseMaster(master.Master):
    def add_log(self, e, level):
        if level in ("warn", "error"):
            raise ScriptError(e)


def tscript(cmd, args=""):
    o = options.Options()
    cmd = example_dir.path(cmd)
    m = RaiseMaster(o, proxy.DummyServer())
    sc = script.Script(cmd)
    m.addons.add(sc)
    return m, sc


class TestScripts(tservers.MasterTest):
    def test_add_header(self):
        m, _ = tscript("simple/add_header.py")
        f = tflow.tflow(resp=tutils.tresp())
        m.addons.handle_lifecycle("response", f)
        assert f.response.headers["newheader"] == "foo"

    def test_custom_contentviews(self):
        m, sc = tscript("simple/custom_contentview.py")
        swapcase = contentviews.get("swapcase")
        _, fmt = swapcase(b"<html>Test!</html>")
        assert any(b'tEST!' in val[0][1] for val in fmt)

    def test_iframe_injector(self):
        with taddons.context() as tctx:
            sc = tctx.script(example_dir.path("simple/modify_body_inject_iframe.py"))
            tctx.configure(
                sc,
                iframe = "http://example.org/evil_iframe"
            )
            f = tflow.tflow(
                resp=tutils.tresp(content=b"<html><body>mitmproxy</body></html>")
            )
            tctx.master.addons.invoke_addon(sc, "response", f)
            content = f.response.content
            assert b'iframe' in content and b'evil_iframe' in content

    def test_modify_form(self):
        m, sc = tscript("simple/modify_form.py")

        form_header = Headers(content_type="application/x-www-form-urlencoded")
        f = tflow.tflow(req=tutils.treq(headers=form_header))
        m.addons.handle_lifecycle("request", f)

        assert f.request.urlencoded_form["mitmproxy"] == "rocks"

        f.request.headers["content-type"] = ""
        m.addons.handle_lifecycle("request", f)
        assert list(f.request.urlencoded_form.items()) == [("foo", "bar")]

    def test_modify_querystring(self):
        m, sc = tscript("simple/modify_querystring.py")
        f = tflow.tflow(req=tutils.treq(path="/search?q=term"))

        m.addons.handle_lifecycle("request", f)
        assert f.request.query["mitmproxy"] == "rocks"

        f.request.path = "/"
        m.addons.handle_lifecycle("request", f)
        assert f.request.query["mitmproxy"] == "rocks"

    def test_redirect_requests(self):
        m, sc = tscript("simple/redirect_requests.py")
        f = tflow.tflow(req=tutils.treq(host="example.org"))
        m.addons.handle_lifecycle("request", f)
        assert f.request.host == "mitmproxy.org"

    def test_send_reply_from_proxy(self):
        m, sc = tscript("simple/send_reply_from_proxy.py")
        f = tflow.tflow(req=tutils.treq(host="example.com", port=80))
        m.addons.handle_lifecycle("request", f)
        assert f.response.content == b"Hello World"

    def test_dns_spoofing(self):
        m, sc = tscript("complex/dns_spoofing.py")
        original_host = "example.com"

        host_header = Headers(host=original_host)
        f = tflow.tflow(req=tutils.treq(headers=host_header, port=80))

        m.addons.handle_lifecycle("requestheaders", f)

        # Rewrite by reverse proxy mode
        f.request.scheme = "https"
        f.request.port = 443

        m.addons.handle_lifecycle("request", f)

        assert f.request.scheme == "http"
        assert f.request.port == 80

        assert f.request.headers["Host"] == original_host
