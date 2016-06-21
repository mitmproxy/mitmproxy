import time

from mitmproxy.builtins import script
from mitmproxy import exceptions
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy import options

from .. import tutils, mastertest


class TestParseCommand:
    def test_empty_command(self):
        with tutils.raises(exceptions.AddonError):
            script.parse_command("")

        with tutils.raises(exceptions.AddonError):
            script.parse_command("  ")

    def test_no_script_file(self):
        with tutils.raises("not found"):
            script.parse_command("notfound")

        with tutils.tmpdir() as dir:
            with tutils.raises("not a file"):
                script.parse_command(dir)

    def test_parse_args(self):
        with tutils.chdir(tutils.test_data.dirname):
            assert script.parse_command("data/scripts/a.py") == ("data/scripts/a.py", [])
            assert script.parse_command("data/scripts/a.py foo bar") == ("data/scripts/a.py", ["foo", "bar"])
            assert script.parse_command("data/scripts/a.py 'foo bar'") == ("data/scripts/a.py", ["foo bar"])

    @tutils.skip_not_windows
    def test_parse_windows(self):
        with tutils.chdir(tutils.test_data.dirname):
            assert script.parse_command("data\\scripts\\a.py") == ("data\\scripts\\a.py", [])
            assert script.parse_command("data\\scripts\\a.py 'foo \\ bar'") == ("data\\scripts\\a.py", 'foo \\ bar', [])


def test_load_script():
    ns = script.load_script(
        tutils.test_data.path(
            "data/addonscripts/recorder.py"
        ), []
    )
    assert ns["configure"]


class RecordingMaster(master.FlowMaster):
    def __init__(self, *args, **kwargs):
        master.FlowMaster.__init__(self, *args, **kwargs)
        self.event_log = []

    def add_event(self, e, level):
        self.event_log.append((level, e))


class TestScript(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        m = master.FlowMaster(options.Options(), None, s)
        sc = script.Script(
            tutils.test_data.path(
                "data/addonscripts/recorder.py"
            )
        )
        m.addons.add(sc)
        assert sc.ns["call_log"] == [("configure", (options.Options(),), {})]

        sc.ns["call_log"] = []
        f = tutils.tflow(resp=True)
        self.invoke(m, "request", f)
        assert sc.ns["call_log"] == [
            ("request", (), {})
        ]

    def test_reload(self):
        s = state.State()
        m = RecordingMaster(options.Options(), None, s)
        with tutils.tmpdir():
            with open("foo.py", "w"):
                pass
            sc = script.Script("foo.py")
            m.addons.add(sc)

            for _ in range(100):
                with open("foo.py", "a") as f:
                    f.write(".")
                time.sleep(0.1)
                if m.event_log:
                    return
            raise AssertionError("Change event not detected.")

    def test_exception(self):
        s = state.State()
        m = RecordingMaster(options.Options(), None, s)
        sc = script.Script(
            tutils.test_data.path("data/addonscripts/error.py")
        )
        m.addons.add(sc)
        f = tutils.tflow(resp=True)
        self.invoke(m, "request", f)
        assert m.event_log[0][0] == "warn"

    def test_duplicate_flow(self):
        s = state.State()
        fm = master.FlowMaster(None, None, s)
        fm.addons.add(
            script.Script(
                tutils.test_data.path("data/addonscripts/duplicate_flow.py")
            )
        )
        f = tutils.tflow()
        fm.request(f)
        assert fm.state.flow_count() == 2
        assert not fm.state.view[0].request.is_replay
        assert fm.state.view[1].request.is_replay


class TestScriptLoader(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        o = options.Options(scripts=[])
        m = master.FlowMaster(o, None, s)
        sc = script.ScriptLoader()
        m.addons.add(sc)
        assert len(m.addons) == 1
        o.update(
            scripts = [
                tutils.test_data.path("data/addonscripts/recorder.py")
            ]
        )
        assert len(m.addons) == 2
        o.update(scripts = [])
        assert len(m.addons) == 1
