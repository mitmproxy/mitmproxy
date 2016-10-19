from .. import tutils, mastertest, tservers
from mitmproxy.builtins import replace
from mitmproxy import master
from mitmproxy import options
from mitmproxy import proxy


class TestReplace(mastertest.MasterTest):
    def test_configure(self):
        r = replace.Replace()
        updated = set(["replacements"])
        r.configure(options.Options(
            replacements=[("one", "two", "three")]
        ), updated)
        tutils.raises(
            "invalid filter pattern",
            r.configure,
            options.Options(
                replacements=[("~b", "two", "three")]
            ),
            updated
        )
        tutils.raises(
            "invalid regular expression",
            r.configure,
            options.Options(
                replacements=[("foo", "+", "three")]
            ),
            updated
        )

    def test_simple(self):
        o = options.Options(
            replacements = [
                ("~q", "foo", "bar"),
                ("~s", "foo", "bar"),
            ]
        )
        m = master.Master(o, proxy.DummyServer())
        sa = replace.Replace()
        m.addons.add(sa)

        f = tutils.tflow()
        f.request.content = b"foo"
        m.request(f)
        assert f.request.content == b"bar"

        f = tutils.tflow(resp=True)
        f.response.content = b"foo"
        m.response(f)
        assert f.response.content == b"bar"


class TestUpstreamProxy(tservers.HTTPUpstreamProxyTest):
    ssl = False

    def test_order(self):
        sa = replace.Replace()
        self.proxy.tmaster.addons.add(sa)

        self.proxy.tmaster.options.replacements = [
            ("~q", "foo", "bar"),
            ("~q", "bar", "baz"),
            ("~q", "foo", "oh noes!"),
            ("~s", "baz", "ORLY")
        ]
        p = self.pathoc()
        with p.connect():
            req = p.request("get:'%s/p/418:b\"foo\"'" % self.server.urlbase)
        assert req.content == b"ORLY"
        assert req.status_code == 418
