import os
import sys
import traceback
from unittest import mock

import pytest

from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy.addons import script
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


def test_load_script():
    ns = script.load_script(
        tutils.test_data.path(
            "mitmproxy/data/addonscripts/recorder/recorder.py"
        )
    )
    assert ns.addons

    with pytest.raises(FileNotFoundError):
        script.load_script(
            "nonexistent"
        )


def test_load_fullname():
    """
    Test that loading two scripts at locations a/foo.py and b/foo.py works.
    This only succeeds if they get assigned different basenames.

    """
    ns = script.load_script(
        tutils.test_data.path(
            "mitmproxy/data/addonscripts/addon.py"
        )
    )
    assert ns.addons
    ns2 = script.load_script(
        tutils.test_data.path(
            "mitmproxy/data/addonscripts/same_filename/addon.py"
        )
    )
    assert ns.name != ns2.name
    assert not hasattr(ns2, "addons")


def test_script_print_stdout():
    with taddons.context() as tctx:
        with mock.patch('mitmproxy.ctx.log.warn') as mock_warn:
            with addonmanager.safecall():
                ns = script.load_script(
                    tutils.test_data.path(
                        "mitmproxy/data/addonscripts/print.py"
                    )
                )
                ns.load(addonmanager.Loader(tctx.master))
        mock_warn.assert_called_once_with("stdoutprint")


class TestScript:
    def test_notfound(self):
        with taddons.context():
            with pytest.raises(exceptions.OptionsError):
                script.Script("nonexistent")

    def test_simple(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/recorder/recorder.py"
                )
            )
            tctx.master.addons.add(sc)
            tctx.configure(sc)
            sc.tick()

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
            sc.tick()
            assert tctx.master.has_log("Loading")
            tctx.master.clear()
            assert not tctx.master.has_log("Loading")

            sc.last_load, sc.last_mtime = 0, 0
            sc.tick()
            assert tctx.master.has_log("Loading")

    def test_exception(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path("mitmproxy/data/addonscripts/error.py")
            )
            tctx.master.addons.add(sc)
            tctx.configure(sc)
            sc.tick()

            f = tflow.tflow(resp=True)
            tctx.master.addons.trigger("request", f)

            assert tctx.master.has_log("ValueError: Error!")
            assert tctx.master.has_log("error.py")

    def test_addon(self):
        with taddons.context() as tctx:
            sc = script.Script(
                tutils.test_data.path(
                    "mitmproxy/data/addonscripts/addon.py"
                )
            )
            tctx.master.addons.add(sc)
            tctx.configure(sc)
            sc.tick()
            assert sc.ns.event_log == [
                'scriptload', 'addonload', 'scriptconfigure', 'addonconfigure'
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
    def test_script_run(self):
        rp = tutils.test_data.path(
            "mitmproxy/data/addonscripts/recorder/recorder.py"
        )
        sc = script.ScriptLoader()
        with taddons.context() as tctx:
            sc.script_run([tflow.tflow(resp=True)], rp)
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'recorder load', 'recorder running', 'recorder configure',
                'recorder tick',
                'recorder requestheaders', 'recorder request',
                'recorder responseheaders', 'recorder response'
            ]

    def test_script_run_nonexistent(self):
        sc = script.ScriptLoader()
        with taddons.context():
            with pytest.raises(exceptions.CommandError):
                sc.script_run([tflow.tflow(resp=True)], "/")

    def test_simple(self):
        sc = script.ScriptLoader()
        with taddons.context() as tctx:
            tctx.master.addons.add(sc)
            sc.running()
            assert len(tctx.master.addons) == 1
            tctx.master.options.update(
                scripts = [
                    tutils.test_data.path(
                        "mitmproxy/data/addonscripts/recorder/recorder.py"
                    )
                ]
            )
            assert len(tctx.master.addons) == 1
            assert len(sc.addons) == 1
            tctx.master.options.update(scripts = [])
            assert len(tctx.master.addons) == 1
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

    def test_script_deletion(self):
        tdir = tutils.test_data.path("mitmproxy/data/addonscripts/")
        with open(tdir + "/dummy.py", 'w') as f:
            f.write("\n")
        with taddons.context() as tctx:
            sl = script.ScriptLoader()
            tctx.master.addons.add(sl)
            tctx.configure(sl, scripts=[tutils.test_data.path("mitmproxy/data/addonscripts/dummy.py")])

            os.remove(tutils.test_data.path("mitmproxy/data/addonscripts/dummy.py"))
            tctx.invoke(sl, "tick")
            assert not tctx.options.scripts
            assert not sl.addons

    def test_load_err(self):
        sc = script.ScriptLoader()
        with taddons.context() as tctx:
            tctx.configure(sc, scripts=[
                tutils.test_data.path("mitmproxy/data/addonscripts/load_error.py")
            ])
            try:
                tctx.invoke(sc, "tick")
            except ValueError:
                pass  # this is expected and normally guarded.
            # on the next tick we should not fail however.
            tctx.invoke(sc, "tick")
            assert len(tctx.master.addons) == 0

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
            tctx.master.addons.invoke_addon(sc, "tick")
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'a load',
                'a running',
                'a configure',
                'a tick',

                'b load',
                'b running',
                'b configure',
                'b tick',

                'c load',
                'c running',
                'c configure',
                'c tick',
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
            tctx.master.addons.invoke_addon(sc, "tick")

            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'c done',
                'b done',
                'a configure',
                'e load',
                'e running',
                'e configure',
                'e tick',
                'a tick',
            ]
