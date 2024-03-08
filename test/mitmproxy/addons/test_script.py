import asyncio
import os
import re
import sys
import traceback

import pytest

from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy.addons import script
from mitmproxy.proxy.layers.http import HttpRequestHook
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.tools import main

# We want this to be speedy for testing
script.ReloadInterval = 0.1


def test_load_script(tmp_path, tdata, caplog):
    ns = script.load_script(
        tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py")
    )
    assert ns.addons

    script.load_script("nonexistent")
    assert "FileNotFoundError" in caplog.text

    (tmp_path / "error.py").write_text("this is invalid syntax")
    script.load_script(str(tmp_path / "error.py"))
    assert "invalid syntax" in caplog.text


def test_load_fullname(tdata):
    """
    Test that loading two scripts at locations a/foo.py and b/foo.py works.
    This only succeeds if they get assigned different basenames.

    """
    ns = script.load_script(tdata.path("mitmproxy/data/addonscripts/addon.py"))
    assert ns.addons
    ns2 = script.load_script(
        tdata.path("mitmproxy/data/addonscripts/same_filename/addon.py")
    )
    assert ns.name != ns2.name
    assert not hasattr(ns2, "addons")


class TestScript:
    def test_notfound(self):
        with taddons.context():
            with pytest.raises(exceptions.OptionsError):
                script.Script("nonexistent", False)

    def test_quotes_around_filename(self, tdata):
        """
        Test that a script specified as '"foo.py"' works to support the calling convention of
        mitmproxy 2.0, as e.g. used by Cuckoo Sandbox.
        """
        path = tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py")

        s = script.Script(f'"{path}"', False)
        assert '"' not in s.fullpath

    async def test_simple(self, tdata, caplog_async):
        caplog_async.set_level("DEBUG")
        sc = script.Script(
            tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py"),
            True,
        )
        with taddons.context(sc) as tctx:
            tctx.configure(sc)
            await caplog_async.await_log("recorder configure")
            rec = tctx.master.addons.get("recorder")

            assert rec.call_log[0][0:2] == ("recorder", "load")

            rec.call_log = []
            f = tflow.tflow(resp=True)
            tctx.master.addons.trigger(HttpRequestHook(f))

            assert rec.call_log[0][1] == "request"
        sc.done()

    async def test_reload(self, tmp_path, caplog_async):
        caplog_async.set_level("INFO")
        with taddons.context() as tctx:
            f = tmp_path / "foo.py"
            f.write_text("\n")
            sc = script.Script(str(f), True)
            tctx.configure(sc)
            await caplog_async.await_log("Loading")
            caplog_async.clear()

            for i in range(20):
                # Some filesystems only have second-level granularity,
                # so just writing once again is not good enough.
                f.write_text("\n")
                if "Loading" in caplog_async.caplog.text:
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("No reload seen")
            sc.done()

    async def test_exception(self, tdata, caplog_async):
        caplog_async.set_level("INFO")
        with taddons.context() as tctx:
            sc = script.Script(
                tdata.path("mitmproxy/data/addonscripts/error.py"),
                True,
            )
            tctx.master.addons.add(sc)
            await caplog_async.await_log("error load")
            tctx.configure(sc)

            f = tflow.tflow(resp=True)
            tctx.master.addons.trigger(HttpRequestHook(f))

            await caplog_async.await_log("ValueError: Error!")
            await caplog_async.await_log("error.py")
            sc.done()

    def test_import_error(self, monkeypatch, tdata, caplog):
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        script.Script(
            tdata.path("mitmproxy/data/addonscripts/import_error.py"),
            reload=False,
        )
        assert (
            "Note that mitmproxy's binaries include their own Python environment"
            in caplog.text
        )

    def test_configure_error(self, tdata, caplog):
        with taddons.context():
            script.Script(
                tdata.path("mitmproxy/data/addonscripts/configure.py"),
                False,
            )
            assert "Options Error" in caplog.text

    async def test_addon(self, tdata, caplog_async):
        caplog_async.set_level("INFO")
        with taddons.context() as tctx:
            sc = script.Script(tdata.path("mitmproxy/data/addonscripts/addon.py"), True)
            tctx.master.addons.add(sc)
            await caplog_async.await_log("addon running")
            assert sc.ns.event_log == [
                "scriptload",
                "addonload",
                "scriptconfigure",
                "addonconfigure",
            ]
            sc.done()


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
    async def test_script_run(self, tdata, caplog_async):
        caplog_async.set_level("DEBUG")
        rp = tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py")
        sc = script.ScriptLoader()
        with taddons.context(sc):
            sc.script_run([tflow.tflow(resp=True)], rp)
            await caplog_async.await_log("recorder response")
            debug = [
                i.msg for i in caplog_async.caplog.records if i.levelname == "DEBUG"
            ]
            assert debug == [
                "recorder configure",
                "recorder running",
                "recorder requestheaders",
                "recorder request",
                "recorder responseheaders",
                "recorder response",
            ]

    async def test_script_run_nonexistent(self, caplog):
        sc = script.ScriptLoader()
        sc.script_run([tflow.tflow(resp=True)], "/")
        assert "No such script" in caplog.text

    async def test_simple(self, tdata):
        sc = script.ScriptLoader()
        with taddons.context(loadcore=False) as tctx:
            tctx.master.addons.add(sc)
            sc.running()
            assert len(tctx.master.addons) == 1
            tctx.master.options.update(
                scripts=[tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py")]
            )
            assert len(tctx.master.addons) == 1
            assert len(sc.addons) == 1
            tctx.master.options.update(scripts=[])
            assert len(tctx.master.addons) == 1
            assert len(sc.addons) == 0

    def test_dupes(self):
        sc = script.ScriptLoader()
        with taddons.context(sc) as tctx:
            with pytest.raises(exceptions.OptionsError):
                tctx.configure(sc, scripts=["one", "one"])

    async def test_script_deletion(self, tdata, caplog_async):
        caplog_async.set_level("INFO")
        tdir = tdata.path("mitmproxy/data/addonscripts/")
        with open(tdir + "/dummy.py", "w") as f:
            f.write("\n")

        with taddons.context() as tctx:
            sl = script.ScriptLoader()
            tctx.master.addons.add(sl)
            tctx.configure(
                sl, scripts=[tdata.path("mitmproxy/data/addonscripts/dummy.py")]
            )
            await caplog_async.await_log("Loading")

            os.remove(tdata.path("mitmproxy/data/addonscripts/dummy.py"))

            await caplog_async.await_log("Removing")
            await asyncio.sleep(0.1)
            assert not tctx.options.scripts
            assert not sl.addons

    async def test_order(self, tdata, caplog_async):
        caplog_async.set_level("DEBUG")
        rec = tdata.path("mitmproxy/data/addonscripts/recorder")
        sc = script.ScriptLoader()
        sc.is_running = True
        with taddons.context(sc) as tctx:
            tctx.configure(
                sc,
                scripts=[
                    "%s/a.py" % rec,
                    "%s/b.py" % rec,
                    "%s/c.py" % rec,
                ],
            )
            await caplog_async.await_log("configure")
            debug = [
                i.msg for i in caplog_async.caplog.records if i.levelname == "DEBUG"
            ]
            assert debug == [
                "a load",
                "a configure",
                "a running",
                "b load",
                "b configure",
                "b running",
                "c load",
                "c configure",
                "c running",
            ]

            caplog_async.clear()
            tctx.configure(
                sc,
                scripts=[
                    "%s/c.py" % rec,
                    "%s/a.py" % rec,
                    "%s/b.py" % rec,
                ],
            )

            await caplog_async.await_log("b configure")
            debug = [
                i.msg for i in caplog_async.caplog.records if i.levelname == "DEBUG"
            ]
            assert debug == [
                "c configure",
                "a configure",
                "b configure",
            ]

            caplog_async.clear()
            tctx.configure(
                sc,
                scripts=[
                    "%s/e.py" % rec,
                    "%s/a.py" % rec,
                ],
            )
            await caplog_async.await_log("e configure")
            debug = [
                i.msg for i in caplog_async.caplog.records if i.levelname == "DEBUG"
            ]
            assert debug == [
                "c done",
                "b done",
                "a configure",
                "e load",
                "e configure",
                "e running",
            ]

            # stop reload tasks
            tctx.configure(sc, scripts=[])


def test_order(tdata, capsys):
    """Integration test: Make sure that the runtime hooks are triggered on startup in the correct order."""
    main.mitmdump(
        [
            "-n",
            "-s",
            tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py"),
            "-s",
            tdata.path("mitmproxy/data/addonscripts/shutdown.py"),
        ]
    )
    time = r"\[[\d:.]+\] "
    out = capsys.readouterr().out
    assert re.match(
        rf"{time}Loading script.+recorder.py\n"
        rf"{time}\('recorder', 'load', .+\n"
        rf"{time}\('recorder', 'configure', .+\n"
        rf"{time}Loading script.+shutdown.py\n"
        rf"{time}\('recorder', 'running', .+\n"
        rf"{time}\('recorder', 'done', .+\n$",
        out,
    )
