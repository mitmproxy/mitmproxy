import traceback

import sys
import time
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy.builtins import script
from mitmproxy.flow import master
from mitmproxy.flow import state

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
        m.addons.add(sc)
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
            m.addons.add(sc)

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
        m.addons.add(sc)
        f = tutils.tflow(resp=True)
        m.request(f)
        assert m.event_log[0][0] == "error"
        assert len(m.event_log[0][1].splitlines()) == 6
        assert 'addonscripts/error.py", line 7, in request' in m.event_log[0][1]
        assert 'addonscripts/error.py", line 3, in mkerr' in m.event_log[0][1]
        assert m.event_log[0][1].endswith("ValueError: Error!\n")

    def test_duplicate_flow(self):
        s = state.State()
        o = options.Options()
        fm = master.FlowMaster(o, None, s)
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

    def test_addon(self):
        s = state.State()
        o = options.Options()
        m = master.FlowMaster(o, None, s)
        sc = script.Script(
            tutils.test_data.path(
                "data/addonscripts/addon.py"
            )
        )
        m.addons.add(sc)
        assert sc.ns.event_log == [
            'scriptstart', 'addonstart', 'addonconfigure'
        ]


class TestCutTraceback:
    def raise_(self, i):
        if i > 0:
            self.raise_(i - 1)
        raise RuntimeError()

    def test_simple(self):
        try:
            self.raise_(4)
        except RuntimeError:
            tb = sys.exc_info()[2]
            tb_cut = script.cut_traceback(tb, "test_simple")
            assert len(traceback.extract_tb(tb_cut)) == 5

            tb_cut2 = script.cut_traceback(tb, "nonexistent")
            assert len(traceback.extract_tb(tb_cut2)) == len(traceback.extract_tb(tb))


class TestScriptLoader(mastertest.MasterTest):
    def test_run_once(self):
        s = state.State()
        o = options.Options(scripts=[])
        m = master.FlowMaster(o, None, s)
        sl = script.ScriptLoader()
        m.addons.add(sl)

        f = tutils.tflow(resp=True)
        with m.handlecontext():
            sc = sl.run_once(
                tutils.test_data.path(
                    "data/addonscripts/recorder.py"
                ), [f]
            )
        evts = [i[1] for i in sc.ns.call_log]
        assert evts == ['start', 'requestheaders', 'request', 'responseheaders', 'response', 'done']

        with m.handlecontext():
            tutils.raises(
                "file not found",
                sl.run_once,
                "nonexistent",
                [f]
            )

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
        m.addons.add(sc)

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
