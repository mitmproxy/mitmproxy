from .. import tutils, mastertest
from mitmproxy.builtins import replace
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy.flow import options


class TestReplace(mastertest.MasterTest):
    def test_configure(self):
        r = replace.Replace()
        r.configure(options.Options(
            replacements=[("one", "two", "three")]
        ))
        tutils.raises(
            "invalid filter pattern",
            r.configure,
            options.Options(
                replacements=[("~b", "two", "three")]
            )
        )
        tutils.raises(
            "invalid regular expression",
            r.configure,
            options.Options(
                replacements=[("foo", "+", "three")]
            )
        )

    def test_simple(self):
        s = state.State()
        m = master.FlowMaster(
            options.Options(
                replacements = [
                    ("~q", "foo", "bar"),
                    ("~s", "foo", "bar"),
                ]
            ),
            None,
            s
        )
        sa = replace.Replace()
        m.addons.add(sa)

        f = tutils.tflow()
        f.request.content = b"foo"
        self.invoke(m, "request", f)
        assert f.request.content == b"bar"

        f = tutils.tflow(resp=True)
        f.response.content = b"foo"
        self.invoke(m, "response", f)
        assert f.response.content == b"bar"
