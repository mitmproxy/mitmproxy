import json

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy.net.http import cookies


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

    def test_simple(self, tmpdir, tdata):
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/complex/har_dump.py"))
            path = str(tmpdir.join("somefile"))
            tctx.configure(a, hardump=path)
            tctx.invoke(a, "response", self.flow())
            tctx.invoke(a, "done")
            with open(path, "r") as inp:
                har = json.load(inp)
            assert len(har["log"]["entries"]) == 1

    def test_base64(self, tmpdir, tdata):
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/complex/har_dump.py"))
            path = str(tmpdir.join("somefile"))
            tctx.configure(a, hardump=path)

            tctx.invoke(
                a, "response", self.flow(resp_content=b"foo" + b"\xFF" * 10)
            )
            tctx.invoke(a, "done")
            with open(path, "r") as inp:
                har = json.load(inp)
            assert har["log"]["entries"][0]["response"]["content"]["encoding"] == "base64"

    def test_format_cookies(self, tdata):
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/complex/har_dump.py"))

            CA = cookies.CookieAttrs

            f = a.format_cookies([("n", "v", CA([("k", "v")]))])[0]
            assert f['name'] == "n"
            assert f['value'] == "v"
            assert not f['httpOnly']
            assert not f['secure']

            f = a.format_cookies([("n", "v", CA([("httponly", None), ("secure", None)]))])[0]
            assert f['httpOnly']
            assert f['secure']

            f = a.format_cookies([("n", "v", CA([("expires", "Mon, 24-Aug-2037 00:00:00 GMT")]))])[0]
            assert f['expires']

    def test_binary(self, tmpdir, tdata):
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/complex/har_dump.py"))
            path = str(tmpdir.join("somefile"))
            tctx.configure(a, hardump=path)

            f = self.flow()
            f.request.method = "POST"
            f.request.headers["content-type"] = "application/x-www-form-urlencoded"
            f.request.content = b"foo=bar&baz=s%c3%bc%c3%9f"
            f.response.headers["random-junk"] = bytes(range(256))
            f.response.content = bytes(range(256))

            tctx.invoke(a, "response", f)
            tctx.invoke(a, "done")

            with open(path, "r") as inp:
                har = json.load(inp)
            assert len(har["log"]["entries"]) == 1
