import json
import shlex
import pytest

from mitmproxy import options
from mitmproxy import proxy
from mitmproxy import master
from mitmproxy.addons import script

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.net.http import cookies

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
        with pytest.raises(ScriptError):
            tscript("complex/har_dump.py")

    def test_simple(self, tmpdir):
        path = str(tmpdir.join("somefile"))

        m, sc = tscript("complex/har_dump.py", shlex.quote(path))
        m.addons.trigger("response", self.flow())
        m.addons.remove(sc)

        with open(path, "r") as inp:
            har = json.load(inp)
        assert len(har["log"]["entries"]) == 1

    def test_base64(self, tmpdir):
        path = str(tmpdir.join("somefile"))

        m, sc = tscript("complex/har_dump.py", shlex.quote(path))
        m.addons.trigger(
            "response", self.flow(resp_content=b"foo" + b"\xFF" * 10)
        )
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

    def test_binary(self, tmpdir):

        f = self.flow()
        f.request.method = "POST"
        f.request.headers["content-type"] = "application/x-www-form-urlencoded"
        f.request.content = b"foo=bar&baz=s%c3%bc%c3%9f"
        f.response.headers["random-junk"] = bytes(range(256))
        f.response.content = bytes(range(256))

        path = str(tmpdir.join("somefile"))

        m, sc = tscript("complex/har_dump.py", shlex.quote(path))
        m.addons.trigger("response", f)
        m.addons.remove(sc)

        with open(path, "r") as inp:
            har = json.load(inp)
        assert len(har["log"]["entries"]) == 1
