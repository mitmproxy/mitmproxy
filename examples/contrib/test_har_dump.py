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
        # context is needed to provide ctx.log function that
        # is invoked if there are exceptions
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/contrib/har_dump.py"))
            # check script is read without errors
            assert tctx.master.logs == []
            assert a.name_value   # last function in har_dump.py

            path = str(tmpdir.join("somefile"))
            tctx.configure(a, hardump=path)
            a.response(self.flow())
            a.done()
            with open(path) as inp:
                har = json.load(inp)
            assert len(har["log"]["entries"]) == 1

    def test_base64(self, tmpdir, tdata):
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/contrib/har_dump.py"))
            path = str(tmpdir.join("somefile"))
            tctx.configure(a, hardump=path)

            a.response(self.flow(resp_content=b"foo" + b"\xFF" * 10))
            a.done()
            with open(path) as inp:
                har = json.load(inp)
            assert har["log"]["entries"][0]["response"]["content"]["encoding"] == "base64"

    def test_format_cookies(self, tdata):
        with taddons.context() as tctx:
            a = tctx.script(tdata.path("../examples/contrib/har_dump.py"))

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
            a = tctx.script(tdata.path("../examples/contrib/har_dump.py"))
            path = str(tmpdir.join("somefile"))
            tctx.configure(a, hardump=path)

            f = self.flow()
            f.request.method = "POST"
            f.request.headers["content-type"] = "application/x-www-form-urlencoded"
            f.request.content = b"foo=bar&baz=s%c3%bc%c3%9f"
            f.response.headers["random-junk"] = bytes(range(256))
            f.response.content = bytes(range(256))

            a.response(f)
            a.done()

            with open(path) as inp:
                har = json.load(inp)
            assert len(har["log"]["entries"]) == 1
