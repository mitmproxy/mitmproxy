import traceback
import sys
import time
import re

from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy.addons import script
from mitmproxy import master

from .. import tutils as ttutils


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
            assert script.parse_command(
                "mitmproxy/data/addonscripts/recorder.py"
            ) == ("mitmproxy/data/addonscripts/recorder.py", [])
            assert script.parse_command(
                "mitmproxy/data/addonscripts/recorder.py foo bar"
            ) == ("mitmproxy/data/addonscripts/recorder.py", ["foo", "bar"])
            assert script.parse_command(
                "mitmproxy/data/addonscripts/recorder.py 'foo bar'"
            ) == ("mitmproxy/data/addonscripts/recorder.py", ["foo bar"])

    @ttutils.skip_not_windows
    def test_parse_windows(self):
        with tutils.chdir(tutils.test_data.dirname):
            assert script.parse_command(
                "mitmproxy/data\\addonscripts\\recorder.py"
            ) == ("mitmproxy/data\\addonscripts\\recorder.py", [])
            assert script.parse_command(
                "mitmproxy/data\\addonscripts\\recorder.py 'foo \\ bar'"
            ) == ("mitmproxy/data\\addonscripts\\recorder.py", ['foo \\ bar'])


def test_load_script():
    ns = script.load_script(
        tutils.test_data.path(
            "mitmproxy/data/addonscripts/recorder.py"
        ), []
    )
    assert ns.start


class TestScript:
    def test_simple(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/recorder.py"
                )
            )
            sc.load_script()
            assert sc.ns.call_log == [
                ("solo", "start", (), {}),
            ]

            sc.ns.call_log = []
            f = tflow.tflow(resp=True)
            sc.request(f)

            recf = sc.ns.call_log[0]
            assert recf[1] == "request"

    def test_reload(self):
        with taddons.context() as tctx:
            with tutils.tmpdir():
                with open("foo.py", "w"):
                    pass
                sc = script.Script("foo.py")
                tctx.configure(sc)
                for _ in range(100):
                    with open("foo.py", "a") as f:
                        f.write(".")
                    sc.tick()
                    time.sleep(0.1)
                    if tctx.master.event_log:
                        return
                raise AssertionError("Change event not detected.")

    def test_exception(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path("mitmproxy/data/addonscripts/error.py")
            )
            sc.start()
            f = tflow.tflow(resp=True)
            sc.request(f)
            assert tctx.master.event_log[0][0] == "error"
            assert len(tctx.master.event_log[0][1].splitlines()) == 6
            assert re.search('addonscripts/error.py", line \d+, in request', tctx.master.event_log[0][1])
            assert re.search('addonscripts/error.py", line \d+, in mkerr', tctx.master.event_log[0][1])
            assert tctx.master.event_log[0][1].endswith("ValueError: Error!\n")

    def test_addon(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/addon.py"
                )
            )
            sc.start()
            tctx.configure(sc)
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


class TestScriptLoader:
    def test_run_once(self):
        o = options.Options(scripts=[])
        m = master.Master(o, proxy.DummyServer())
        sl = script.ScriptLoader()
        m.addons.add(sl)

        f = tflow.tflow(resp=True)
        with m.handlecontext():
            sc = sl.run_once(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/recorder.py"
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
        o = options.Options(scripts=[])
        m = master.Master(o, proxy.DummyServer())
        sc = script.ScriptLoader()
        m.addons.add(sc)
        assert len(m.addons) == 1
        o.update(
            scripts = [
                tutils.test_data.path("mitmproxy/data/addonscripts/recorder.py")
            ]
        )
        assert len(m.addons) == 2
        o.update(scripts = [])
        assert len(m.addons) == 1

    def test_dupes(self):
        o = options.Options(scripts=["one", "one"])
        m = master.Master(o, proxy.DummyServer())
        sc = script.ScriptLoader()
        tutils.raises(exceptions.OptionsError, m.addons.add, o, sc)

    def test_order(self):
        rec = tutils.test_data.path("mitmproxy/data/addonscripts/recorder.py")
        sc = script.ScriptLoader()
        with taddons.context() as tctx:
            tctx.master.addons.add(sc)
            tctx.configure(
                sc,
                scripts = [
                    "%s %s" % (rec, "a"),
                    "%s %s" % (rec, "b"),
                    "%s %s" % (rec, "c"),
                ]
            )
            debug = [(i[0], i[1]) for i in tctx.master.event_log if i[0] == "debug"]
            assert debug == [
                ('debug', 'a start'), ('debug', 'a configure'),
                ('debug', 'b start'), ('debug', 'b configure'),
                ('debug', 'c start'), ('debug', 'c configure')
            ]
            tctx.master.event_log = []
            tctx.configure(
                sc,
                scripts = [
                    "%s %s" % (rec, "c"),
                    "%s %s" % (rec, "a"),
                    "%s %s" % (rec, "b"),
                ]
            )
            debug = [(i[0], i[1]) for i in tctx.master.event_log if i[0] == "debug"]
            # No events, only order has changed
            assert debug == []

            tctx.master.event_log = []
            tctx.configure(
                sc,
                scripts = [
                    "%s %s" % (rec, "x"),
                    "%s %s" % (rec, "a"),
                ]
            )
            debug = [(i[0], i[1]) for i in tctx.master.event_log if i[0] == "debug"]
            assert debug == [
                ('debug', 'c done'),
                ('debug', 'b done'),
                ('debug', 'x start'),
                ('debug', 'x configure'),
            ]
