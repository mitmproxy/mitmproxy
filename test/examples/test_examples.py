from mitmproxy import contentviews
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy.net.http import Headers

from ..mitmproxy import tservers

example_dir = tutils.test_data.push("../examples")


class TestScripts(tservers.MasterTest):
    def test_add_header(self):
        with taddons.context() as tctx:
            a = tctx.script(example_dir.path("simple/add_header.py"))
            f = tflow.tflow(resp=tutils.tresp())
            a.response(f)
            assert f.response.headers["newheader"] == "foo"

    def test_custom_contentviews(self):
        with taddons.context() as tctx:
            tctx.script(example_dir.path("simple/custom_contentview.py"))
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
        with taddons.context() as tctx:
            sc = tctx.script(example_dir.path("simple/modify_form.py"))

            form_header = Headers(content_type="application/x-www-form-urlencoded")
            f = tflow.tflow(req=tutils.treq(headers=form_header))
            sc.request(f)

            assert f.request.urlencoded_form["mitmproxy"] == "rocks"

            f.request.headers["content-type"] = ""
            sc.request(f)
            assert list(f.request.urlencoded_form.items()) == [("foo", "bar")]

    def test_modify_querystring(self):
        with taddons.context() as tctx:
            sc = tctx.script(example_dir.path("simple/modify_querystring.py"))
            f = tflow.tflow(req=tutils.treq(path="/search?q=term"))

            sc.request(f)
            assert f.request.query["mitmproxy"] == "rocks"

            f.request.path = "/"
            sc.request(f)
            assert f.request.query["mitmproxy"] == "rocks"

    def test_redirect_requests(self):
        with taddons.context() as tctx:
            sc = tctx.script(example_dir.path("simple/redirect_requests.py"))
            f = tflow.tflow(req=tutils.treq(host="example.org"))
            sc.request(f)
            assert f.request.host == "mitmproxy.org"

    def test_send_reply_from_proxy(self):
        with taddons.context() as tctx:
            sc = tctx.script(example_dir.path("simple/send_reply_from_proxy.py"))
            f = tflow.tflow(req=tutils.treq(host="example.com", port=80))
            sc.request(f)
            assert f.response.content == b"Hello World"

    def test_dns_spoofing(self):
        with taddons.context() as tctx:
            sc = tctx.script(example_dir.path("complex/dns_spoofing.py"))

            original_host = "example.com"

            host_header = Headers(host=original_host)
            f = tflow.tflow(req=tutils.treq(headers=host_header, port=80))

            tctx.master.addons.invoke_addon(sc, "requestheaders", f)

            # Rewrite by reverse proxy mode
            f.request.scheme = "https"
            f.request.port = 443

            tctx.master.addons.invoke_addon(sc, "request", f)

            assert f.request.scheme == "http"
            assert f.request.port == 80

            assert f.request.headers["Host"] == original_host
