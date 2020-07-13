import pytest

from mitmproxy.addons import mapremote
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestMapRemote:

    def test_configure(self):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(mr, map_remote=["one/two/three"])
            with pytest.raises(Exception, match="Cannot parse map_remote .* Invalid number"):
                tctx.configure(mr, map_remote=["/"])
            with pytest.raises(Exception, match="Cannot parse map_remote .* Invalid filter"):
                tctx.configure(mr, map_remote=["/~b/two/three"])
            with pytest.raises(Exception, match="Cannot parse map_remote .* Invalid regular expression"):
                tctx.configure(mr, map_remote=["/foo/+/three"])
            tctx.configure(mr, map_remote=["/a/b/c/"])

    def test_simple(self):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(
                mr,
                map_remote=[
                    ":example.org/images/:mitmproxy.org/img/",
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            mr.request(f)
            assert f.request.url == "https://mitmproxy.org/img/test.jpg"

    def test_has_reply(self):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(mr, map_remote=[":example.org:mitmproxy.org"])
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            f.kill()
            mr.request(f)
            assert f.request.url == "https://example.org/images/test.jpg"


class TestMapRemoteFile:
    def test_simple(self, tmpdir):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tmpfile = tmpdir.join("replacement")
            tmpfile.write("mitmproxy.org")
            tctx.configure(
                mr,
                map_remote=["|example.org|@" + str(tmpfile)]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/test"
            mr.request(f)
            assert f.request.url == "https://mitmproxy.org/test"

    @pytest.mark.asyncio
    async def test_nonexistent(self, tmpdir):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            with pytest.raises(Exception, match="Invalid file path"):
                tctx.configure(
                    mr,
                    map_remote=[":~q:example.org:@nonexistent"]
                )

            tmpfile = tmpdir.join("replacement")
            tmpfile.write("mitmproxy.org")
            tctx.configure(
                mr,
                map_remote=["|example.org|@" + str(tmpfile)]
            )
            tmpfile.remove()
            f = tflow.tflow()
            f.request.url = b"https://example.org/test"
            mr.request(f)
            assert await tctx.master.await_log("could not read")
