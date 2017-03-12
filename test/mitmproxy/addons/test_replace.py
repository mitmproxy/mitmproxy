import os.path

import pytest

from mitmproxy.addons import replace
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


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
                replacements=[
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

    def test_order(self):
        r = replace.Replace()
        with taddons.context() as tctx:
            tctx.configure(
                r,
                replacements=[
                    "/foo/bar",
                    "/bar/baz",
                    "/foo/oh noes!",
                    "/bar/oh noes!",
                ]
            )
            f = tflow.tflow()
            f.request.content = b"foo"
            r.request(f)
            assert f.request.content == b"baz"


class TestReplaceFile:
    def test_simple(self):
        r = replace.Replace()
        with tutils.tmpdir() as td:
            rp = os.path.join(td, "replacement")
            with open(rp, "w") as f:
                f.write("bar")
            with taddons.context() as tctx:
                tctx.configure(
                    r,
                    replacements=[
                        "/~q/foo/@" + rp,
                        "/~s/foo/@" + rp,
                        "/~b nonexistent/nonexistent/@nonexistent",
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
