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
            assert script.parse_command("data/addonscripts/recorder.py") == ("data/addonscripts/recorder.py", [])
            assert script.parse_command("data/addonscripts/recorder.py foo bar") == ("data/addonscripts/recorder.py", ["foo", "bar"])
            assert script.parse_command("data/addonscripts/recorder.py 'foo bar'") == ("data/addonscripts/recorder.py", ["foo bar"])

    @tutils.skip_not_windows
    def test_parse_windows(self):
        with tutils.chdir(tutils.test_data.dirname):
            assert script.parse_command(
                "data\\addonscripts\\recorder.py"
            ) == ("data\\addonscripts\\recorder.py", [])
            assert script.parse_command(
                "data\\addonscripts\\recorder.py 'foo \\ bar'"
            ) == ("data\\addonscripts\\recorder.py", ['foo \\ bar'])


def test_load_script():
    ns = script.load_script(
        tutils.test_data.path(
            "data/addonscripts/recorder.py"
        ), []
    )
    assert ns.start


class TestScript(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        o = options.Options()
        m = master.FlowMaster(o, None, s)
        sc = script.Script(
            tutils.test_data.path(
                "data/addonscripts/recorder.py"
            )
        )
        m.addons.add(o, sc)
        assert sc.ns.call_log == [
            ("solo", "start", (), {}),
            ("solo", "configure", (o, o.keys()), {})
        ]

        sc.ns.call_log = []
        f = tutils.tflow(resp=True)
        m.request(f)

        recf = sc.ns.call_log[0]
        assert recf[1] == "request"

    def test_reload(self):
        s = state.State()
        o = options.Options()
        m = mastertest.RecordingMaster(o, None, s)
        with tutils.tmpdir():
            with open("foo.py", "w"):
                pass
            sc = script.Script("foo.py")
            m.addons.add(o, sc)

            for _ in range(100):
                with open("foo.py", "a") as f:
                    f.write(".")
                m.addons.invoke_with_context(sc, "tick")
                time.sleep(0.1)
                if m.event_log:
                    return
            raise AssertionError("Change event not detected.")

    def test_exception(self):
        s = state.State()
        o = options.Options()
        m = mastertest.RecordingMaster(o, None, s)
        sc = script.Script(
            tutils.test_data.path("data/addonscripts/error.py")
        )
        m.addons.add(o, sc)
        f = tutils.tflow(resp=True)
        m.request(f)
        assert m.event_log[0][0] == "error"

    def test_duplicate_flow(self):
        s = state.State()
        o = options.Options()
        fm = master.FlowMaster(o, None, s)
        fm.addons.add(
            o,
            script.Script(
                tutils.test_data.path("data/addonscripts/duplicate_flow.py")
            )
        )
        f = tutils.tflow()
        fm.request(f)
        assert fm.state.flow_count() == 2
        assert not fm.state.view[0].request.is_replay
        assert fm.state.view[1].request.is_replay

    def test_addon(self):
        s = state.State()
        o = options.Options()
        m = master.FlowMaster(o, None, s)
        sc = script.Script(
            tutils.test_data.path(
                "data/addonscripts/addon.py"
            )
        )
        m.addons.add(o, sc)
        assert sc.ns.event_log == [
            'scriptstart', 'addonstart', 'addonconfigure'
        ]


class TestScriptLoader(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        o = options.Options(scripts=[])
        m = master.FlowMaster(o, None, s)
        sc = script.ScriptLoader()
        m.addons.add(o, sc)
        assert len(m.addons) == 1
        o.update(
            scripts = [
                tutils.test_data.path("data/addonscripts/recorder.py")
            ]
        )
        assert len(m.addons) == 2
        o.update(scripts = [])
        assert len(m.addons) == 1

    def test_dupes(self):
        s = state.State()
        o = options.Options(scripts=["one", "one"])
        m = master.FlowMaster(o, None, s)
        sc = script.ScriptLoader()
        tutils.raises(exceptions.OptionsError, m.addons.add, o, sc)

    def test_order(self):
        rec = tutils.test_data.path("data/addonscripts/recorder.py")

        s = state.State()
        o = options.Options(
            scripts = [
                "%s %s" % (rec, "a"),
                "%s %s" % (rec, "b"),
                "%s %s" % (rec, "c"),
            ]
        )
        m = mastertest.RecordingMaster(o, None, s)
        sc = script.ScriptLoader()
        m.addons.add(o, sc)

        debug = [(i[0], i[1]) for i in m.event_log if i[0] == "debug"]
        assert debug == [
            ('debug', 'a start'), ('debug', 'a configure'),
            ('debug', 'b start'), ('debug', 'b configure'),
            ('debug', 'c start'), ('debug', 'c configure')
        ]
        m.event_log[:] = []

        o.scripts = [
            "%s %s" % (rec, "c"),
            "%s %s" % (rec, "a"),
            "%s %s" % (rec, "b"),
        ]
        debug = [(i[0], i[1]) for i in m.event_log if i[0] == "debug"]
        assert debug == [
            ('debug', 'c configure'),
            ('debug', 'a configure'),
            ('debug', 'b configure'),
        ]
        m.event_log[:] = []

        o.scripts = [
            "%s %s" % (rec, "x"),
            "%s %s" % (rec, "a"),
        ]
        debug = [(i[0], i[1]) for i in m.event_log if i[0] == "debug"]
        assert debug == [
            ('debug', 'c done'),
            ('debug', 'b done'),
            ('debug', 'x start'),
            ('debug', 'x configure'),
            ('debug', 'a configure'),
        ]
