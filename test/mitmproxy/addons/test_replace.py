import os.path
import pytest
from mitmproxy.test import tflow
from mitmproxy.test import tutils

from .. import tservers
from mitmproxy.addons import replace
from mitmproxy.test import taddons


class TestReplace:
    def test_parse_hook(self):
        x = replace.parse_hook("/foo/bar/voing")
        assert x == ("foo", "bar", "voing")
        x = replace.parse_hook("/foo/bar/vo/ing/")
        assert x == ("foo", "bar", "vo/ing/")
        x = replace.parse_hook("/bar/voing")
        assert x == (".*", "bar", "voing")
        with pytest.raises(Exception, match="Invalid replacement"):
            replace.parse_hook("/")

    def test_configure(self):
        r = replace.Replace()
        with taddons.context() as tctx:
            tctx.configure(r, replacements=["one/two/three"])
            with pytest.raises(Exception, match="Invalid filter pattern"):
                tctx.configure(r, replacements=["/~b/two/three"])
            with pytest.raises(Exception, match="Invalid regular expression"):
                tctx.configure(r, replacements=["/foo/+/three"])
            tctx.configure(r, replacements=["/a/b/c/"])

    def test_simple(self):
        r = replace.Replace()
        with taddons.context() as tctx:
            tctx.configure(
                r,
                replacements = [
                    "/~q/foo/bar",
                    "/~s/foo/bar",
                ]
            )
            f = tflow.tflow()
            f.request.content = b"foo"
            r.request(f)
            assert f.request.content == b"bar"

            f = tflow.tflow(resp=True)
            f.response.content = b"foo"
            r.response(f)
            assert f.response.content == b"bar"


class TestUpstreamProxy(tservers.HTTPUpstreamProxyTest):
    ssl = False

    def test_order(self):
        sa = replace.Replace()
        self.proxy.tmaster.addons.add(sa)

        self.proxy.tmaster.options.replacements = [
            "/~q/foo/bar",
            "/~q/bar/baz",
            "/~q/foo/oh noes!",
            "/~s/baz/ORLY"
        ]
        p = self.pathoc()
        with p.connect():
            req = p.request("get:'%s/p/418:b\"foo\"'" % self.server.urlbase)
        assert req.content == b"ORLY"
        assert req.status_code == 418


class TestReplaceFile:
    def test_simple(self):
        r = replace.ReplaceFile()
        with tutils.tmpdir() as td:
            rp = os.path.join(td, "replacement")
            with open(rp, "w") as f:
                f.write("bar")
            with taddons.context() as tctx:
                tctx.configure(
                    r,
                    replacement_files = [
                        "/~q/foo/" + rp,
                        "/~s/foo/" + rp,
                        "/~b nonexistent/nonexistent/nonexistent",
                    ]
                )
                f = tflow.tflow()
                f.request.content = b"foo"
                r.request(f)
                assert f.request.content == b"bar"

                f = tflow.tflow(resp=True)
                f.response.content = b"foo"
                r.response(f)
                assert f.response.content == b"bar"

                f = tflow.tflow()
                f.request.content = b"nonexistent"
                assert not tctx.master.event_log
                r.request(f)
                assert tctx.master.event_log
