from mitmproxy import contentviews
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy.http import Headers

from ..mitmproxy import tservers


class TestScripts(tservers.MasterTest):
    def test_add_header(self, tdata):
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/addons/anatomy2.py"))
            f = tflow.tflow()
            a.request(f)
            assert f.request.headers["myheader"] == "value"

    def test_custom_contentviews(self, tdata):
        with taddons.context() as tctx:
            tctx.script(tdata.path("../examples/addons/contentview.py"))
            swapcase = contentviews.get("swapcase")
            _, fmt = swapcase(b"<html>Test!</html>")
            assert any(b'tEST!' in val[0][1] for val in fmt)

    def test_modify_form(self, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(tdata.path("../examples/addons/http-modify-form.py"))

            form_header = Headers(content_type="application/x-www-form-urlencoded")
            f = tflow.tflow(req=tutils.treq(headers=form_header))
            sc.request(f)

            assert f.request.urlencoded_form["mitmproxy"] == "rocks"

            f.request.headers["content-type"] = ""
            sc.request(f)
            assert list(f.request.urlencoded_form.items()) == [("foo", "bar")]

    def test_modify_querystring(self, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(tdata.path("../examples/addons/http-modify-query-string.py"))
            f = tflow.tflow(req=tutils.treq(path="/search?q=term"))

            sc.request(f)
            assert f.request.query["mitmproxy"] == "rocks"

            f.request.path = "/"
            sc.request(f)
            assert f.request.query["mitmproxy"] == "rocks"

    def test_redirect_requests(self, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(tdata.path("../examples/addons/http-redirect-requests.py"))
            f = tflow.tflow(req=tutils.treq(host="example.org"))
            sc.request(f)
            assert f.request.host == "mitmproxy.org"

    def test_send_reply_from_proxy(self, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(tdata.path("../examples/addons/http-reply-from-proxy.py"))
            f = tflow.tflow(req=tutils.treq(host="example.com", port=80))
            sc.request(f)
            assert f.response.content == b"Hello World"
