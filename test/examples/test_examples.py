from mitmproxy import contentviews
from mitmproxy.http import Headers
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestScripts:
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
            assert any(b"tEST!" in val[0][1] for val in fmt)

    def test_custom_grpc_contentview(self, tdata):
        with taddons.context() as tctx:
            tctx.script(tdata.path("../examples/addons/contentview-custom-grpc.py"))
            v = contentviews.get("customized gRPC/protobuf")

            p = tdata.path("mitmproxy/contentviews/test_grpc_data/msg1.bin")
            with open(p, "rb") as f:
                raw = f.read()

            sim_msg_req = tutils.treq(
                port=443, host="example.com", path="/ReverseGeocode"
            )

            sim_msg_resp = tutils.tresp()

            sim_flow = tflow.tflow(req=sim_msg_req, resp=sim_msg_resp)

            view_text, output = v(
                raw, flow=sim_flow, http_message=sim_flow.request
            )  # simulate request message
            assert view_text == "Protobuf (flattened) (addon with custom rules)"
            output = list(output)  # assure list conversion if generator
            assert output == [
                [
                    ("text", "[message]  "),
                    ("text", "position   "),
                    ("text", "1    "),
                    ("text", "                               "),
                ],
                [
                    ("text", "[double]   "),
                    ("text", "latitude   "),
                    ("text", "1.1  "),
                    ("text", "38.89816675798073              "),
                ],
                [
                    ("text", "[double]   "),
                    ("text", "longitude  "),
                    ("text", "1.2  "),
                    ("text", "-77.03829828366696             "),
                ],
                [
                    ("text", "[string]   "),
                    ("text", "country    "),
                    ("text", "3    "),
                    ("text", "de_DE                          "),
                ],
                [
                    ("text", "[uint32]   "),
                    ("text", "           "),
                    ("text", "6    "),
                    ("text", "1                              "),
                ],
                [
                    ("text", "[string]   "),
                    ("text", "app        "),
                    ("text", "7    "),
                    ("text", "de.mcdonalds.mcdonaldsinfoapp  "),
                ],
            ]

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
            sc = tctx.script(
                tdata.path("../examples/addons/http-modify-query-string.py")
            )
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
