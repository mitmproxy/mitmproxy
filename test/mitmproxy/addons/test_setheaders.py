import pytest

from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons import setheaders


class TestSetHeaders:
    def test_parse_setheaders(self):
        x = setheaders.parse_setheader("/foo/bar/voing")
        assert x == ("foo", "bar", "voing")
        x = setheaders.parse_setheader("/foo/bar/vo/ing/")
        assert x == ("foo", "bar", "vo/ing/")
        x = setheaders.parse_setheader("/bar/voing")
        assert x == (".*", "bar", "voing")
        with pytest.raises(Exception, match="Invalid replacement"):
            setheaders.parse_setheader("/")

    def test_configure(self):
        sh = setheaders.SetHeaders()
        with taddons.context() as tctx:
            with pytest.raises(Exception, match="Invalid setheader filter pattern"):
                tctx.configure(sh, setheaders = ["/~b/one/two"])
            tctx.configure(sh, setheaders = ["/foo/bar/voing"])

    def test_setheaders(self):
        sh = setheaders.SetHeaders()
        with taddons.context() as tctx:
            tctx.configure(
                sh,
                setheaders = [
                    "/~q/one/two",
                    "/~s/one/three"
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
                setheaders = [
                    "/~s/one/two",
                    "/~s/one/three"
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.headers["one"] = "xxx"
            f.response.headers["one"] = "xxx"
            sh.response(f)
            assert f.response.headers.get_all("one") == ["two", "three"]

            tctx.configure(
                sh,
                setheaders = [
                    "/~q/one/two",
                    "/~q/one/three"
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            sh.request(f)
            assert f.request.headers.get_all("one") == ["two", "three"]
