from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons

from mitmproxy.addons import setheaders
from mitmproxy import options


class TestSetHeaders:
    def test_configure(self):
        sh = setheaders.SetHeaders()
        o = options.Options(
            setheaders = [("~b", "one", "two")]
        )
        tutils.raises(
            "invalid setheader filter pattern",
            sh.configure, o, o.keys()
        )

    def test_setheaders(self):
        sh = setheaders.SetHeaders()
        with taddons.context() as tctx:
            tctx.configure(
                sh,
                setheaders = [
                    ("~q", "one", "two"),
                    ("~s", "one", "three")
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
                    ("~s", "one", "two"),
                    ("~s", "one", "three")
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
                    ("~q", "one", "two"),
                    ("~q", "one", "three")
                ]
            )
            f = tflow.tflow()
            f.request.headers["one"] = "xxx"
            sh.request(f)
            assert f.request.headers.get_all("one") == ["two", "three"]
