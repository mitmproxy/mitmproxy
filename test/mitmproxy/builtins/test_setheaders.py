from .. import tutils, mastertest

from mitmproxy.builtins import setheaders
from mitmproxy.flow import state
from mitmproxy.flow import options


class TestSetHeaders(mastertest.MasterTest):
    def mkmaster(self, **opts):
        s = state.State()
        m = mastertest.RecordingMaster(options.Options(**opts), None, s)
        sh = setheaders.SetHeaders()
        m.addons.add(sh)
        return m, sh

    def test_configure(self):
        sh = setheaders.SetHeaders()
        tutils.raises(
            "invalid setheader filter pattern",
            sh.configure,
            options.Options(
                setheaders = [("~b", "one", "two")]
            )
        )

    def test_setheaders(self):
        m, sh = self.mkmaster(
            setheaders = [
                ("~q", "one", "two"),
                ("~s", "one", "three")
            ]
        )
        f = tutils.tflow()
        f.request.headers["one"] = "xxx"
        self.invoke(m, "request", f)
        assert f.request.headers["one"] == "two"

        f = tutils.tflow(resp=True)
        f.response.headers["one"] = "xxx"
        self.invoke(m, "response", f)
        assert f.response.headers["one"] == "three"

        m, sh = self.mkmaster(
            setheaders = [
                ("~s", "one", "two"),
                ("~s", "one", "three")
            ]
        )
        f = tutils.tflow(resp=True)
        f.request.headers["one"] = "xxx"
        f.response.headers["one"] = "xxx"
        self.invoke(m, "response", f)
        assert f.response.headers.get_all("one") == ["two", "three"]

        m, sh = self.mkmaster(
            setheaders = [
                ("~q", "one", "two"),
                ("~q", "one", "three")
            ]
        )
        f = tutils.tflow()
        f.request.headers["one"] = "xxx"
        self.invoke(m, "request", f)
        assert f.request.headers.get_all("one") == ["two", "three"]
