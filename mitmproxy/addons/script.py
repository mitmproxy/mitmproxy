import asyncio
import importlib.machinery
import importlib.util
import logging
import os
import sys
import types
from collections.abc import Sequence

import mitmproxy.types as mtypes
from mitmproxy import addonmanager
from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import eventsequence
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import hooks
from mitmproxy.utils import asyncio_utils

logger = logging.getLogger(__name__)


def load_script(path: str) -> types.ModuleType | None:
    fullname = "__mitmproxy_script__.{}".format(
        os.path.splitext(os.path.basename(path))[0]
    )
    # the fullname is not unique among scripts, so if there already is an existing script with said
    # fullname, remove it.
    sys.modules.pop(fullname, None)
    oldpath = sys.path
    sys.path.insert(0, os.path.dirname(path))
    m = None
    try:
        loader = importlib.machinery.SourceFileLoader(fullname, path)
        spec = importlib.util.spec_from_loader(fullname, loader=loader)
        assert spec
        m = importlib.util.module_from_spec(spec)
        loader.exec_module(m)
        if not getattr(m, "name", None):
            m.name = path  # type: ignore
    except ImportError as e:
        if getattr(sys, "frozen", False):
            e.msg += (
                f".\n"
                f"Note that mitmproxy's binaries include their own Python environment. "
                f"If your addon requires the installation of additional dependencies, "
                f"please install mitmproxy from PyPI "
                f"(https://docs.mitmproxy.org/stable/overview-installation/#installation-from-the-python-package-index-pypi)."
            )
        script_error_handler(path, e)
    except Exception as e:
        script_error_handler(path, e)
    finally:
        sys.path[:] = oldpath
        return m


def script_error_handler(path: str, exc: Exception) -> None:
    """
    Log errors during script loading.
    """
    tback = exc.__traceback__
    tback = addonmanager.cut_traceback(
        tback, "invoke_addon_sync"
    )  # we're calling configure() on load
    tback = addonmanager.cut_traceback(
        tback, "_call_with_frames_removed"
    )  # module execution from importlib
    logger.error(f"error in script {path}", exc_info=(type(exc), exc, tback))


ReloadInterval = 1


class Script:
    """
    An addon that manages a single script.
    """

    def __init__(self, path: str, reload: bool) -> None:
        self.name = "scriptmanager:" + path
        self.path = path
        self.fullpath = os.path.expanduser(path.strip("'\" "))
        self.ns: types.ModuleType | None = None
        self.is_running = False

        if not os.path.isfile(self.fullpath):
            raise exceptions.OptionsError(f"No such script: {self.fullpath}")

        self.reloadtask = None
        if reload:
            self.reloadtask = asyncio_utils.create_task(
                self.watcher(),
                name=f"script watcher for {path}",
                keep_ref=False,
            )
        else:
            self.loadscript()

    def running(self):
        self.is_running = True

    def done(self):
        if self.reloadtask:
            self.reloadtask.cancel()

    @property
    def addons(self):
        return [self.ns] if self.ns else []

    def loadscript(self):
        logger.info("Loading script %s" % self.path)
        if self.ns:
            ctx.master.addons.remove(self.ns)
        self.ns = None
        with addonmanager.safecall():
            ns = load_script(self.fullpath)
            ctx.master.addons.register(ns)
            self.ns = ns
        if self.ns:
            try:
                ctx.master.addons.invoke_addon_sync(
                    self.ns, hooks.ConfigureHook(ctx.options.keys())
                )
            except Exception as e:
                script_error_handler(self.fullpath, e)
            if self.is_running:
                # We're already running, so we call that on the addon now.
                ctx.master.addons.invoke_addon_sync(self.ns, hooks.RunningHook())

    async def watcher(self):
        # Script loading is terminally confused at the moment.
        # This here is a stopgap workaround to defer loading.
        await asyncio.sleep(0)
        last_mtime = 0.0
        while True:
            try:
                mtime = os.stat(self.fullpath).st_mtime
            except FileNotFoundError:
                logger.info("Removing script %s" % self.path)
                scripts = list(ctx.options.scripts)
                scripts.remove(self.path)
                ctx.options.update(scripts=scripts)
                return
            if mtime > last_mtime:
                self.loadscript()
                last_mtime = mtime
            await asyncio.sleep(ReloadInterval)


class ScriptLoader:
    """
    An addon that manages loading scripts from options.
    """

    def __init__(self):
        self.is_running = False
        self.addons = []

    def load(self, loader):
        loader.add_option("scripts", Sequence[str], [], "Execute a script.")

    def running(self):
        self.is_running = True

    @command.command("script.run")
    def script_run(self, flows: Sequence[flow.Flow], path: mtypes.Path) -> None:
        """
        Run a script on the specified flows. The script is configured with
        the current options and all lifecycle events for each flow are
        simulated. Note that the load event is not invoked.
        """
        if not os.path.isfile(path):
            logger.error("No such script: %s" % path)
            return
        mod = load_script(path)
        if mod:
            with addonmanager.safecall():
                ctx.master.addons.invoke_addon_sync(
                    mod,
                    hooks.ConfigureHook(ctx.options.keys()),
                )
                ctx.master.addons.invoke_addon_sync(mod, hooks.RunningHook())
                for f in flows:
                    for evt in eventsequence.iterate(f):
                        ctx.master.addons.invoke_addon_sync(mod, evt)

    def configure(self, updated):
        if "scripts" in updated:
            for s in ctx.options.scripts:
                if ctx.options.scripts.count(s) > 1:
                    raise exceptions.OptionsError("Duplicate script")

            for a in self.addons[:]:
                if a.path not in ctx.options.scripts:
                    logger.info("Un-loading script: %s" % a.path)
                    ctx.master.addons.remove(a)
                    self.addons.remove(a)

            # The machinations below are to ensure that:
            #   - Scripts remain in the same order
            #   - Scripts are not initialized un-necessarily. If only a
            #   script's order in the script list has changed, it is just
            #   moved.

            current = {}
            for a in self.addons:
                current[a.path] = a

            ordered = []
            newscripts = []
            for s in ctx.options.scripts:
                if s in current:
                    ordered.append(current[s])
                else:
                    sc = Script(s, True)
                    ordered.append(sc)
                    newscripts.append(sc)

            self.addons = ordered

            for s in newscripts:
                ctx.master.addons.register(s)
                if self.is_running:
                    # If we're already running, we configure and tell the addon
                    # we're up and running.
                    ctx.master.addons.invoke_addon_sync(s, hooks.RunningHook())
