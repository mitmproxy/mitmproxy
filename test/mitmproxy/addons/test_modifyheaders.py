import pytest

from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons import modifyheaders


class TestModifyHeaders:
    def test_parse_modify_spec(self):
        x = modifyheaders.parse_modify_spec("/foo/bar/voing")
        assert [x[0], x[2], x[3]] == ["foo", b"bar", b"voing"]

        x = modifyheaders.parse_modify_spec("/foo/bar/vo/ing/")
        assert [x[0], x[2], x[3]] == ["foo", b"bar", b"vo/ing/"]

        x = modifyheaders.parse_modify_spec("/bar/voing")
        assert [x[0], x[2], x[3]] == [".*", b"bar", b"voing"]

        with pytest.raises(Exception, match="Invalid number of parameters"):
            modifyheaders.parse_modify_spec("/")

        with pytest.raises(Exception, match="Invalid filter pattern"):
            modifyheaders.parse_modify_spec("/~b/one/two")

        with pytest.raises(Exception, match="Invalid file path"):
            modifyheaders.parse_modify_spec("/~q/foo/@nonexistent")

    def test_configure(self):
        mh = modifyheaders.ModifyHeaders()
        with taddons.context(mh) as tctx:
            with pytest.raises(Exception, match="Cannot parse modify_headers .* Invalid number"):
                tctx.configure(mh, modify_headers = ["/"])

            with pytest.raises(Exception, match="Cannot parse modify_headers .* Invalid filter"):
                tctx.configure(mh, modify_headers = ["/~b/one/two"])

            with pytest.raises(Exception, match="Cannot parse modify_headers .* Invalid file"):
                tctx.configure(mh, modify_headers = ["/~q/foo/@nonexistent"])

            tctx.configure(mh, modify_headers = ["/foo/bar/voing"])

    def test_modify_headers(self):
        mh = modifyheaders.ModifyHeaders()
        with taddons.context(mh) as tctx:
            tctx.configure(
                mh,
                modify_headers = [
                    "/~q/one/two",
                    "/~s/one/three"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            mh.request(f)
            assert f.request.headers["one"] == "two"

            f = tflow.tflow(resp=True)
            f.response.headers["one"] = "xxx"
            mh.response(f)
            assert f.response.headers["one"] == "three"

            tctx.configure(
                mh,
                modify_headers = [
                    "/~s/one/two",
                    "/~s/one/three"
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.headers["one"] = "xxx"
            f.response.headers["one"] = "xxx"
            mh.response(f)
            assert f.response.headers.get_all("one") == ["two", "three"]

            tctx.configure(
                mh,
                modify_headers = [
                    "/~q/one/two",
                    "/~q/one/three"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            mh.request(f)
            assert f.request.headers.get_all("one") == ["two", "three"]

            # test removal of existing headers
            tctx.configure(
                mh,
                modify_headers = [
                    "/~q/one/",
                    "/~s/one/"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            mh.request(f)
            assert "one" not in f.request.headers

            f = tflow.tflow(resp=True)
            f.response.headers["one"] = "xxx"
            mh.response(f)
            assert "one" not in f.response.headers

            tctx.configure(
                mh,
                modify_headers = [
                    "/one/"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            mh.request(f)
            assert "one" not in f.request.headers

            f = tflow.tflow(resp=True)
            f.response.headers["one"] = "xxx"
            mh.response(f)
            assert "one" not in f.response.headers


class TestModifyHeadersFile:
    def test_simple(self, tmpdir):
        mh = modifyheaders.ModifyHeaders()
        with taddons.context(mh) as tctx:
            tmpfile = tmpdir.join("replacement")
            tmpfile.write("two")
            tctx.configure(
                mh,
                modify_headers=["/~q/one/@" + str(tmpfile)]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            mh.request(f)
            assert f.request.headers["one"] == "two"

    @pytest.mark.asyncio
    async def test_nonexistent(self, tmpdir):
        mh = modifyheaders.ModifyHeaders()
        with taddons.context(mh) as tctx:
            with pytest.raises(Exception, match="Cannot parse modify_headers .* Invalid file path"):
                tctx.configure(
                    mh,
                    modify_headers=["/~q/foo/@nonexistent"]
                )

            tmpfile = tmpdir.join("replacement")
            tmpfile.write("bar")
            tctx.configure(
                mh,
                modify_headers=["/~q/foo/@" + str(tmpfile)]
            )
            tmpfile.remove()
            f = tflow.tflow()
            f.request.content = b"foo"
            mh.request(f)
            assert await tctx.master.await_log("could not read")
