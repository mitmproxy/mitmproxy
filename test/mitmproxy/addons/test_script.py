import traceback
import sys
import time
import watchdog.events
import pytest

from unittest import mock
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy import master
from mitmproxy.addons import script


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


def test_load_script():
    with taddons.context() as tctx:
        ns = script.load_script(
            tctx.ctx(),
            tutils.test_data.path(
                "mitmproxy/data/addonscripts/recorder/recorder.py"
            )
        )
        assert ns.addons

        ns = script.load_script(
            tctx.ctx(),
            "nonexistent"
        )
        assert not ns


def test_script_print_stdout():
    with taddons.context() as tctx:
        with mock.patch('mitmproxy.ctx.log.warn') as mock_warn:
            with addonmanager.safecall():
                ns = script.load_script(
                    tctx.ctx(),
                    tutils.test_data.path(
                        "mitmproxy/data/addonscripts/print.py"
                    )
                )
                ns.load(addonmanager.Loader(tctx.master))
        mock_warn.assert_called_once_with("stdoutprint")


class TestScript:
    def test_notfound(self):
        with taddons.context() as tctx:
            sc = script.Script("nonexistent")
            tctx.master.addons.add(sc)

    def test_simple(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/recorder/recorder.py"
                )
            )
            tctx.master.addons.add(sc)

            rec = tctx.master.addons.get("recorder")

            assert rec.call_log[0][0:2] == ("recorder", "load")

            rec.call_log = []
            f = tflow.tflow(resp=True)
            tctx.master.addons.trigger("request", f)

            assert rec.call_log[0][1] == "request"

    def test_reload(self, tmpdir):
        with taddons.context() as tctx:
            f = tmpdir.join("foo.py")
            f.ensure(file=True)
            f.write("\n")
            sc = script.Script(str(f))
            tctx.configure(sc)
            for _ in range(5):
                sc.reload()
                sc.tick()
                time.sleep(0.1)

    def test_exception(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path("mitmproxy/data/addonscripts/error.py")
            )
            tctx.master.addons.add(sc)
            f = tflow.tflow(resp=True)
            tctx.master.addons.trigger("request", f)

            assert tctx.master.logs[0].level == "error"
            tctx.master.has_log("ValueError: Error!")
            tctx.master.has_log("error.py")

    def test_addon(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/addon.py"
                )
            )
            tctx.master.addons.add(sc)
            assert sc.ns.event_log == [
                'scriptload', 'addonload'
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
            tb_cut = addonmanager.cut_traceback(tb, "test_simple")
            assert len(traceback.extract_tb(tb_cut)) == 5

            tb_cut2 = addonmanager.cut_traceback(tb, "nonexistent")
            assert len(traceback.extract_tb(tb_cut2)) == len(traceback.extract_tb(tb))


class TestScriptLoader:
    def test_simple(self):
        o = options.Options(scripts=[])
        m = master.Master(o, proxy.DummyServer())
        sc = script.ScriptLoader()
        sc.running()
        m.addons.add(sc)
        assert len(m.addons) == 1
        o.update(
            scripts = [
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/recorder/recorder.py"
                )
            ]
        )
        assert len(m.addons) == 1
        assert len(sc.addons) == 1
        o.update(scripts = [])
        assert len(m.addons) == 1
        assert len(sc.addons) == 0

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
            tctx.configure(sc, scripts = ["nonexistent"])
            tctx.master.has_log("nonexistent: file not found")

    def test_order(self):
        rec = tutils.test_data.path("mitmproxy/data/addonscripts/recorder")
        sc = script.ScriptLoader()
        sc.is_running = True
        with taddons.context() as tctx:
            tctx.configure(
                sc,
                scripts = [
                    "%s/a.py" % rec,
                    "%s/b.py" % rec,
                    "%s/c.py" % rec,
                ]
            )

            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'a load',
                'a running',

                'b load',
                'b running',

                'c load',
                'c running',

                'a configure',
                'b configure',
                'c configure',
            ]

            tctx.master.logs = []
            tctx.configure(
                sc,
                scripts = [
                    "%s/c.py" % rec,
                    "%s/a.py" % rec,
                    "%s/b.py" % rec,
                ]
            )
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'c configure',
                'a configure',
                'b configure',
            ]

            tctx.master.logs = []
            tctx.configure(
                sc,
                scripts = [
                    "%s/e.py" % rec,
                    "%s/a.py" % rec,
                ]
            )

            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'c done',
                'b done',
                'e load',
                'e running',
                'e configure',
                'a configure',
            ]
