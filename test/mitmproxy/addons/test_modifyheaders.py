import pytest

from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons import modifyheaders


class TestModifyHeaders:
    def test_parse_modifyheaders(self):
        x = modifyheaders.parse_modify_headers("/foo/bar/voing")
        assert x == ("foo", "bar", "voing")
        x = modifyheaders.parse_modify_headers("/foo/bar/vo/ing/")
        assert x == ("foo", "bar", "vo/ing/")
        x = modifyheaders.parse_modify_headers("/bar/voing")
        assert x == ("bar", "voing", ".*")
        with pytest.raises(Exception, match="Invalid replacement"):
            modifyheaders.parse_modify_headers("/")

    def test_configure(self):
        sh = modifyheaders.ModifyHeaders()
        with taddons.context(sh) as tctx:
            with pytest.raises(Exception, match="Invalid modify_headers flow filter"):
                tctx.configure(sh, modify_headers = ["/one/two/~b"])
            tctx.configure(sh, modify_headers = ["/foo/bar/voing"])

    def test_modify_headers(self):
        sh = modifyheaders.ModifyHeaders()
        with taddons.context(sh) as tctx:
            tctx.configure(
                sh,
                modify_headers = [
                    "/one/two/~q",
                    "/one/three/~s"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            sh.request(f)
            assert f.request.headers["one"] == "two"

            f = tflow.tflow(resp=True)
            f.response.headers["one"] = "xxx"
            sh.response(f)
            assert f.response.headers["one"] == "three"

            tctx.configure(
                sh,
                modify_headers = [
                    "/one/two/~s",
                    "/one/three/~s"
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.headers["one"] = "xxx"
            f.response.headers["one"] = "xxx"
            sh.response(f)
            assert f.response.headers.get_all("one") == ["two", "three"]

            tctx.configure(
                sh,
                modify_headers = [
                    "/one/two/~q",
                    "/one/three/~q"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            sh.request(f)
            assert f.request.headers.get_all("one") == ["two", "three"]

            # test removal of existing headers
            tctx.configure(
                sh,
                modify_headers = [
                    "/one//~q",
                    "/one//~s"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            sh.request(f)
            assert "one" not in f.request.headers

            f = tflow.tflow(resp=True)
            f.response.headers["one"] = "xxx"
            sh.response(f)
            assert "one" not in f.response.headers

            tctx.configure(
                sh,
                modify_headers = [
                    "/one/"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            sh.request(f)
            assert "one" not in f.request.headers

            f = tflow.tflow(resp=True)
            f.response.headers["one"] = "xxx"
            sh.response(f)
            assert "one" not in f.response.headers