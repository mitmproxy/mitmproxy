import traceback
import sys
import time
import re
import watchdog.events
import pytest

from unittest import mock
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy import master
from mitmproxy import utils
from mitmproxy.addons import script

from ...conftest import skip_not_windows


def test_scriptenv():
    with taddons.context() as tctx:
        with script.scriptenv("path", []):
            raise SystemExit
        assert tctx.master.has_log("exited", "error")

        tctx.master.clear()
        with script.scriptenv("path", []):
            raise ValueError("fooo")
        assert tctx.master.has_log("fooo", "error")


class Called:
    def __init__(self):
        self.called = False

    def __call__(self, *args, **kwargs):
        self.called = True


def test_reloadhandler():
    rh = script.ReloadHandler(Called())
    assert not rh.filter(watchdog.events.DirCreatedEvent("path"))
    assert not rh.filter(watchdog.events.FileModifiedEvent("/foo/.bar"))
    assert not rh.filter(watchdog.events.FileModifiedEvent("/foo/bar"))
    assert rh.filter(watchdog.events.FileModifiedEvent("/foo/bar.py"))

    assert not rh.callback.called
    rh.on_modified(watchdog.events.FileModifiedEvent("/foo/bar"))
    assert not rh.callback.called
    rh.on_modified(watchdog.events.FileModifiedEvent("/foo/bar.py"))
    assert rh.callback.called
    rh.callback.called = False

    rh.on_created(watchdog.events.FileCreatedEvent("foo"))
    assert not rh.callback.called
    rh.on_created(watchdog.events.FileCreatedEvent("foo.py"))
    assert rh.callback.called


class TestParseCommand:
    def test_empty_command(self):
        with pytest.raises(ValueError):
            script.parse_command("")

        with pytest.raises(ValueError):
            script.parse_command("  ")

    def test_no_script_file(self, tmpdir):
        with pytest.raises(Exception, match="not found"):
            script.parse_command("notfound")

        with pytest.raises(Exception, match="Not a file"):
            script.parse_command(str(tmpdir))

    def test_parse_args(self):
        with utils.chdir(tutils.test_data.dirname):
            assert script.parse_command(
                "mitmproxy/data/addonscripts/recorder.py"
            ) == ("mitmproxy/data/addonscripts/recorder.py", [])
            assert script.parse_command(
                "mitmproxy/data/addonscripts/recorder.py foo bar"
            ) == ("mitmproxy/data/addonscripts/recorder.py", ["foo", "bar"])
            assert script.parse_command(
                "mitmproxy/data/addonscripts/recorder.py 'foo bar'"
            ) == ("mitmproxy/data/addonscripts/recorder.py", ["foo bar"])

    @skip_not_windows
    def test_parse_windows(self):
        with utils.chdir(tutils.test_data.dirname):
            assert script.parse_command(
                "mitmproxy/data\\addonscripts\\recorder.py"
            ) == ("mitmproxy/data\\addonscripts\\recorder.py", [])
            assert script.parse_command(
                "mitmproxy/data\\addonscripts\\recorder.py 'foo \\ bar'"
            ) == ("mitmproxy/data\\addonscripts\\recorder.py", ['foo \\ bar'])


def test_load_script():
    with taddons.context():
        ns = script.load_script(
            tutils.test_data.path(
                "mitmproxy/data/addonscripts/recorder.py"
            ), []
        )
        assert ns.start


def test_script_print_stdout():
    with taddons.context() as tctx:
        with mock.patch('mitmproxy.ctx.log.warn') as mock_warn:
            with script.scriptenv("path", []):
                ns = script.load_script(
                    tutils.test_data.path(
                        "mitmproxy/data/addonscripts/print.py"
                    ), []
                )
                ns.start(tctx.options)
        mock_warn.assert_called_once_with("stdoutprint")


class TestScript:
    def test_simple(self):
        with taddons.context():
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/recorder.py"
                )
            )
            sc.load_script()
            assert sc.ns.call_log[0][0:2] == ("solo", "start")

            sc.ns.call_log = []
            f = tflow.tflow(resp=True)
            sc.request(f)

            recf = sc.ns.call_log[0]
            assert recf[1] == "request"

    def test_reload(self, tmpdir):
        with taddons.context() as tctx:
            f = tmpdir.join("foo.py")
            f.ensure(file=True)
            sc = script.Script(str(f))
            tctx.configure(sc)
            for _ in range(100):
                f.write(".")
                sc.tick()
                time.sleep(0.1)
                if tctx.master.logs:
                    return
            raise AssertionError("Change event not detected.")

    def test_exception(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path("mitmproxy/data/addonscripts/error.py")
            )
            sc.start(tctx.options)
            f = tflow.tflow(resp=True)
            sc.request(f)
            assert tctx.master.logs[0].level == "error"
            assert len(tctx.master.logs[0].msg.splitlines()) == 6
            assert re.search(r'addonscripts[\\/]error.py", line \d+, in request', tctx.master.logs[0].msg)
            assert re.search(r'addonscripts[\\/]error.py", line \d+, in mkerr', tctx.master.logs[0].msg)
            assert tctx.master.logs[0].msg.endswith("ValueError: Error!\n")

    def test_addon(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/addon.py"
                )
            )
            sc.start(tctx.options)
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

        f = tflow.tflow(resp=True)
        with m.handlecontext():
            with pytest.raises(Exception, match="file not found"):
                sl.run_once("nonexistent", [f])

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
        sc = script.ScriptLoader()
        with taddons.context() as tctx:
            tctx.master.addons.add(sc)
            with pytest.raises(exceptions.OptionsError):
                tctx.configure(
                    sc,
                    scripts = ["one", "one"]
                )

    def test_nonexistent(self):
        sc = script.ScriptLoader()
        with taddons.context() as tctx:
            tctx.master.addons.add(sc)
            with pytest.raises(exceptions.OptionsError):
                tctx.configure(
                    sc,
                    scripts = ["nonexistent"]
                )

    def test_order(self):
        rec = tutils.test_data.path("mitmproxy/data/addonscripts/recorder.py")
        sc = script.ScriptLoader()
        with taddons.context() as tctx:
            tctx.master.addons.add(sc)
            sc.running()
            tctx.configure(
                sc,
                scripts = [
                    "%s %s" % (rec, "a"),
                    "%s %s" % (rec, "b"),
                    "%s %s" % (rec, "c"),
                ]
            )
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'a start',
                'a configure',
                'a running',

                'b start',
                'b configure',
                'b running',

                'c start',
                'c configure',
                'c running',
            ]
            tctx.master.logs = []
            tctx.configure(
                sc,
                scripts = [
                    "%s %s" % (rec, "c"),
                    "%s %s" % (rec, "a"),
                    "%s %s" % (rec, "b"),
                ]
            )
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == []

            tctx.master.logs = []
            tctx.configure(
                sc,
                scripts = [
                    "%s %s" % (rec, "x"),
                    "%s %s" % (rec, "a"),
                ]
            )
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'c done',
                'b done',
                'x start',
                'x configure',
                'x running',
            ]
