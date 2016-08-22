from .. import tutils, mastertest
from mitmproxy.builtins import replace
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy import options


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
        s = state.State()
        o = options.Options(
            replacements = [
                ("~q", "foo", "bar"),
                ("~s", "foo", "bar"),
            ]
        )
        m = master.FlowMaster(o, None, s)
        sa = replace.Replace()
        m.addons.add(o, sa)

        f = tutils.tflow()
        f.request.content = b"foo"
        m.request(f)
        assert f.request.content == b"bar"

        f = tutils.tflow(resp=True)
        f.response.content = b"foo"
        m.response(f)
        assert f.response.content == b"bar"
