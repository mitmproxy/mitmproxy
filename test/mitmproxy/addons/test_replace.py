import pytest

from mitmproxy.addons import replace
from mitmproxy.test import taddons
from mitmproxy.test import tflow


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
        with taddons.context(r) as tctx:
            tctx.configure(r, replacements=["one/two/three"])
            with pytest.raises(Exception, match="Invalid filter pattern"):
                tctx.configure(r, replacements=["/~b/two/three"])
            with pytest.raises(Exception, match="Invalid regular expression"):
                tctx.configure(r, replacements=["/foo/+/three"])
            tctx.configure(r, replacements=["/a/b/c/"])

    def test_simple(self):
        r = replace.Replace()
        with taddons.context(r) as tctx:
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
        with taddons.context(r) as tctx:
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
    def test_simple(self, tmpdir):
        r = replace.Replace()
        with taddons.context(r) as tctx:
            tmpfile = tmpdir.join("replacement")
            tmpfile.write("bar")
            tctx.configure(
                r,
                replacements=["/~q/foo/@" + str(tmpfile)]
            )
            f = tflow.tflow()
            f.request.content = b"foo"
            r.request(f)
            assert f.request.content == b"bar"

    @pytest.mark.asyncio
    async def test_nonexistent(self, tmpdir):
        r = replace.Replace()
        with taddons.context(r) as tctx:
            with pytest.raises(Exception, match="Invalid file path"):
                tctx.configure(
                    r,
                    replacements=["/~q/foo/@nonexistent"]
                )

            tmpfile = tmpdir.join("replacement")
            tmpfile.write("bar")
            tctx.configure(
                r,
                replacements=["/~q/foo/@" + str(tmpfile)]
            )
            tmpfile.remove()
            f = tflow.tflow()
            f.request.content = b"foo"
            r.request(f)
            assert await tctx.master.await_log("could not read")
