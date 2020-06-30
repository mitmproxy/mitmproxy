import pytest

from mitmproxy.addons import modifybody
from mitmproxy.addons.modifyheaders import parse_modify_hook
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestModifyBody:
    def test_parse_modify_hook(self):
        x = parse_modify_hook("/foo/bar/voing")
        assert x == ("foo", b"bar", b"voing")
        x = parse_modify_hook("/foo/bar/vo/ing/")
        assert x == ("foo", b"bar", b"vo/ing/")
        x = parse_modify_hook("/bar/voing")
        assert x == (".*", b"bar", b"voing")
        with pytest.raises(Exception, match="Invalid modify_\\* specifier"):
            parse_modify_hook("/")

    def test_configure(self):
        mb = modifybody.ModifyBody()
        with taddons.context(mb) as tctx:
            tctx.configure(mb, modify_body=["one/two/three"])
            with pytest.raises(Exception, match="Invalid modify_body option"):
                tctx.configure(mb, modify_body = ["/"])
            with pytest.raises(Exception, match="Invalid modify_body flow filter"):
                tctx.configure(mb, modify_body=["/~b/two/three"])
            with pytest.raises(Exception, match="Invalid regular expression"):
                tctx.configure(mb, modify_body=["/foo/+/three"])
            tctx.configure(mb, modify_body=["/a/b/c/"])

    def test_simple(self):
        mb = modifybody.ModifyBody()
        with taddons.context(mb) as tctx:
            tctx.configure(
                mb,
                modify_body=[
                    "/~q/foo/bar",
                    "/~s/foo/bar",
                ]
            )
            f = tflow.tflow()
            f.request.content = b"foo"
            mb.request(f)
            assert f.request.content == b"bar"

            f = tflow.tflow(resp=True)
            f.response.content = b"foo"
            mb.response(f)
            assert f.response.content == b"bar"

    def test_order(self):
        mb = modifybody.ModifyBody()
        with taddons.context(mb) as tctx:
            tctx.configure(
                mb,
                modify_body=[
                    "/foo/bar",
                    "/bar/baz",
                    "/foo/oh noes!",
                    "/bar/oh noes!",
                ]
            )
            f = tflow.tflow()
            f.request.content = b"foo"
            mb.request(f)
            assert f.request.content == b"baz"


class TestModifyBodyFile:
    def test_simple(self, tmpdir):
        mb = modifybody.ModifyBody()
        with taddons.context(mb) as tctx:
            tmpfile = tmpdir.join("replacement")
            tmpfile.write("bar")
            tctx.configure(
                mb,
                modify_body=["/~q/foo/@" + str(tmpfile)]
            )
            f = tflow.tflow()
            f.request.content = b"foo"
            mb.request(f)
            assert f.request.content == b"bar"

    @pytest.mark.asyncio
    async def test_nonexistent(self, tmpdir):
        mb = modifybody.ModifyBody()
        with taddons.context(mb) as tctx:
            with pytest.raises(Exception, match="Invalid file path"):
                tctx.configure(
                    mb,
                    modify_body=["/~q/foo/@nonexistent"]
                )

            tmpfile = tmpdir.join("replacement")
            tmpfile.write("bar")
            tctx.configure(
                mb,
                modify_body=["/~q/foo/@" + str(tmpfile)]
            )
            tmpfile.remove()
            f = tflow.tflow()
            f.request.content = b"foo"
            mb.request(f)
            assert await tctx.master.await_log("could not read")
