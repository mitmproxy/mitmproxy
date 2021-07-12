import asyncio
import os
import sys
import traceback

import pytest

from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy.addons import script
from mitmproxy.proxy.layers.http import HttpRequestHook
from mitmproxy.test import taddons
from mitmproxy.test import tflow


# We want this to be speedy for testing
script.ReloadInterval = 0.1


@pytest.mark.asyncio
async def test_load_script(tdata):
    with taddons.context() as tctx:
        ns = script.load_script(
            tdata.path(
                "mitmproxy/data/addonscripts/recorder/recorder.py"
            )
        )
        assert ns.addons

        script.load_script(
            "nonexistent"
        )
        await tctx.master.await_log("No such file or directory")

        script.load_script(
            tdata.path(
                "mitmproxy/data/addonscripts/recorder/error.py"
            )
        )
        await tctx.master.await_log("invalid syntax")


def test_load_fullname(tdata):
    """
    Test that loading two scripts at locations a/foo.py and b/foo.py works.
    This only succeeds if they get assigned different basenames.

    """
    ns = script.load_script(
        tdata.path(
            "mitmproxy/data/addonscripts/addon.py"
        )
    )
    assert ns.addons
    ns2 = script.load_script(
        tdata.path(
            "mitmproxy/data/addonscripts/same_filename/addon.py"
        )
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

        s = script.Script(
            f'"{path}"',
            False
        )
        assert '"' not in s.fullpath

    @pytest.mark.asyncio
    async def test_simple(self, tdata):
        sc = script.Script(
            tdata.path(
                "mitmproxy/data/addonscripts/recorder/recorder.py"
            ),
            True,
        )
        with taddons.context(sc) as tctx:
            tctx.configure(sc)
            await tctx.master.await_log("recorder running")
            rec = tctx.master.addons.get("recorder")

            assert rec.call_log[0][0:2] == ("recorder", "load")

            rec.call_log = []
            f = tflow.tflow(resp=True)
            tctx.master.addons.trigger(HttpRequestHook(f))

            assert rec.call_log[0][1] == "request"

    @pytest.mark.asyncio
    async def test_reload(self, tmpdir):
        with taddons.context() as tctx:
            f = tmpdir.join("foo.py")
            f.ensure(file=True)
            f.write("\n")
            sc = script.Script(str(f), True)
            tctx.configure(sc)
            await tctx.master.await_log("Loading")

            tctx.master.clear()
            for i in range(20):
                f.write("\n")
                if tctx.master.has_log("Loading"):
                    break
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("No reload seen")

    @pytest.mark.asyncio
    async def test_exception(self, tdata):
        with taddons.context() as tctx:
            sc = script.Script(
                tdata.path("mitmproxy/data/addonscripts/error.py"),
                True,
            )
            tctx.master.addons.add(sc)
            await tctx.master.await_log("error running")
            tctx.configure(sc)

            f = tflow.tflow(resp=True)
            tctx.master.addons.trigger(HttpRequestHook(f))

            await tctx.master.await_log("ValueError: Error!")
            await tctx.master.await_log("error.py")

    @pytest.mark.asyncio
    async def test_optionexceptions(self, tdata):
        with taddons.context() as tctx:
            sc = script.Script(
                tdata.path("mitmproxy/data/addonscripts/configure.py"),
                True,
            )
            tctx.master.addons.add(sc)
            tctx.configure(sc)
            await tctx.master.await_log("Options Error")

    @pytest.mark.asyncio
    async def test_addon(self, tdata):
        with taddons.context() as tctx:
            sc = script.Script(
                tdata.path(
                    "mitmproxy/data/addonscripts/addon.py"
                ),
                True
            )
            tctx.master.addons.add(sc)
            await tctx.master.await_log("addon running")
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
    @pytest.mark.asyncio
    async def test_script_run(self, tdata):
        rp = tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py")
        sc = script.ScriptLoader()
        with taddons.context(sc) as tctx:
            sc.script_run([tflow.tflow(resp=True)], rp)
            await tctx.master.await_log("recorder response")
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'recorder running', 'recorder configure',
                'recorder requestheaders', 'recorder request',
                'recorder responseheaders', 'recorder response'
            ]

    @pytest.mark.asyncio
    async def test_script_run_nonexistent(self):
        sc = script.ScriptLoader()
        with taddons.context(sc) as tctx:
            sc.script_run([tflow.tflow(resp=True)], "/")
            await tctx.master.await_log("No such script")

    @pytest.mark.asyncio
    async def test_simple(self, tdata):
        sc = script.ScriptLoader()
        with taddons.context(loadcore=False) as tctx:
            tctx.master.addons.add(sc)
            sc.running()
            assert len(tctx.master.addons) == 1
            tctx.master.options.update(
                scripts = [
                    tdata.path(
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
        with taddons.context(sc) as tctx:
            with pytest.raises(exceptions.OptionsError):
                tctx.configure(
                    sc,
                    scripts = ["one", "one"]
                )

    @pytest.mark.asyncio
    async def test_script_deletion(self, tdata):
        tdir = tdata.path("mitmproxy/data/addonscripts/")
        with open(tdir + "/dummy.py", 'w') as f:
            f.write("\n")

        with taddons.context() as tctx:
            sl = script.ScriptLoader()
            tctx.master.addons.add(sl)
            tctx.configure(sl, scripts=[tdata.path("mitmproxy/data/addonscripts/dummy.py")])
            await tctx.master.await_log("Loading")

            os.remove(tdata.path("mitmproxy/data/addonscripts/dummy.py"))

            await tctx.master.await_log("Removing")
            await asyncio.sleep(0.1)
            assert not tctx.options.scripts
            assert not sl.addons

    @pytest.mark.asyncio
    async def test_script_error_handler(self):
        path = "/sample/path/example.py"
        exc = SyntaxError
        msg = "Error raised"
        tb = True
        with taddons.context() as tctx:
            script.script_error_handler(path, exc, msg, tb)
            await tctx.master.await_log("/sample/path/example.py")
            await tctx.master.await_log("Error raised")
            await tctx.master.await_log("lineno")
            await tctx.master.await_log("NoneType")

    @pytest.mark.asyncio
    async def test_order(self, tdata):
        rec = tdata.path("mitmproxy/data/addonscripts/recorder")
        sc = script.ScriptLoader()
        sc.is_running = True
        with taddons.context(sc) as tctx:
            tctx.configure(
                sc,
                scripts = [
                    "%s/a.py" % rec,
                    "%s/b.py" % rec,
                    "%s/c.py" % rec,
                ]
            )
            await tctx.master.await_log("configure")
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'a load',
                'a running',
                'a configure',

                'b load',
                'b running',
                'b configure',

                'c load',
                'c running',
                'c configure',
            ]

            tctx.master.clear()
            tctx.configure(
                sc,
                scripts = [
                    "%s/c.py" % rec,
                    "%s/a.py" % rec,
                    "%s/b.py" % rec,
                ]
            )

            await tctx.master.await_log("b configure")
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'c configure',
                'a configure',
                'b configure',
            ]

            tctx.master.clear()
            tctx.configure(
                sc,
                scripts = [
                    "%s/e.py" % rec,
                    "%s/a.py" % rec,
                ]
            )
            await tctx.master.await_log("e configure")
            debug = [i.msg for i in tctx.master.logs if i.level == "debug"]
            assert debug == [
                'c done',
                'b done',
                'a configure',
                'e load',
                'e running',
                'e configure',
            ]
