import pytest

from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons.modifyheaders import parse_modify_spec, ModifyHeaders


def test_parse_modify_spec():
    spec = parse_modify_spec("/foo/bar/voing", True)
    assert spec.matches.pattern == "foo"
    assert spec.subject == b"bar"
    assert spec.read_replacement() == b"voing"

    spec = parse_modify_spec("/foo/bar/vo/ing/", False)
    assert spec.matches.pattern == "foo"
    assert spec.subject == b"bar"
    assert spec.read_replacement() == b"vo/ing/"

    spec = parse_modify_spec("/bar/voing", False)
    assert spec.matches(tflow.tflow())
    assert spec.subject == b"bar"
    assert spec.read_replacement() == b"voing"

    with pytest.raises(ValueError, match="Invalid regular expression"):
        parse_modify_spec("/[/two", True)


class TestModifyHeaders:

    def test_configure(self):
        mh = ModifyHeaders()
        with taddons.context(mh) as tctx:
            with pytest.raises(Exception, match="Cannot parse modify_headers"):
                tctx.configure(mh, modify_headers=["/"])
            tctx.configure(mh, modify_headers=["/foo/bar/voing"])

    def test_modify_headers(self):
        mh = ModifyHeaders()
        with taddons.context(mh) as tctx:
            tctx.configure(
                mh,
                modify_headers=[
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
                modify_headers=[
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
                modify_headers=[
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
                modify_headers=[
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
                modify_headers=[
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
        mh = ModifyHeaders()
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
        mh = ModifyHeaders()
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
