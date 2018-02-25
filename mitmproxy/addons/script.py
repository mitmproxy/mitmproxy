import os
import importlib.util
import importlib.machinery
import time
import sys
import types
import typing

from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import command
from mitmproxy import eventsequence
from mitmproxy import ctx


def load_script(path: str) -> types.ModuleType:
    fullname = "__mitmproxy_script__.{}".format(
        os.path.splitext(os.path.basename(path))[0]
    )
    # the fullname is not unique among scripts, so if there already is an existing script with said
    # fullname, remove it.
    sys.modules.pop(fullname, None)
    oldpath = sys.path
    sys.path.insert(0, os.path.dirname(path))
    try:
        loader = importlib.machinery.SourceFileLoader(fullname, path)
        spec = importlib.util.spec_from_loader(fullname, loader=loader)
        m = importlib.util.module_from_spec(spec)
        loader.exec_module(m)
        if not getattr(m, "name", None):
            m.name = path  # type: ignore
        return m
    except Exception as e:
        ctx.log.error(str(e))
    finally:
        sys.path[:] = oldpath


class Script:
    """
        An addon that manages a single script.
    """
    ReloadInterval = 2

    def __init__(self, path):
        self.name = "scriptmanager:" + path
        self.path = path
        self.fullpath = os.path.expanduser(
            path.strip("'\" ")
        )
        self.ns = None

        self.last_load = 0
        self.last_mtime = 0
        if not os.path.isfile(self.fullpath):
            raise exceptions.OptionsError('No such script: "%s"' % self.fullpath)

    @property
    def addons(self):
        return [self.ns] if self.ns else []

    def tick(self):
        if time.time() - self.last_load > self.ReloadInterval:
            try:
                mtime = os.stat(self.fullpath).st_mtime
            except FileNotFoundError:
                scripts = list(ctx.options.scripts)
                scripts.remove(self.path)
                ctx.options.update(scripts=scripts)
                return

            if mtime > self.last_mtime:
                ctx.log.info("Loading script: %s" % self.path)
                if self.ns:
                    ctx.master.addons.remove(self.ns)
                self.ns = None
                with addonmanager.safecall():
                    ns = load_script(self.fullpath)
                    ctx.master.addons.register(ns)
                    self.ns = ns
                if self.ns:
                    # We're already running, so we have to explicitly register and
                    # configure the addon
                    ctx.master.addons.invoke_addon(self.ns, "running")
                    ctx.master.addons.invoke_addon(
                        self.ns,
                        "configure",
                        ctx.options.keys()
                    )
                self.last_load = time.time()
                self.last_mtime = mtime


class ScriptLoader:
    """
        An addon that manages loading scripts from options.
    """
    def __init__(self):
        self.is_running = False
        self.addons = []

    def running(self):
        self.is_running = True

    @command.command("script.run")
    def script_run(self, flows: typing.Sequence[flow.Flow], path: str) -> None:
        """
            Run a script on the specified flows. The script is loaded with
            default options, and all lifecycle events for each flow are
            simulated.
        """
        try:
            s = Script(path)
            l = addonmanager.Loader(ctx.master)
            ctx.master.addons.invoke_addon(s, "load", l)
            ctx.master.addons.invoke_addon(s, "configure", ctx.options.keys())
            # Script is loaded on the first tick
            ctx.master.addons.invoke_addon(s, "tick")
            for f in flows:
                for evt, arg in eventsequence.iterate(f):
                    ctx.master.addons.invoke_addon(s, evt, arg)
        except exceptions.OptionsError as e:
            raise exceptions.CommandError("Error running script: %s" % e) from e

    def configure(self, updated):
        if "scripts" in updated:
            for s in ctx.options.scripts:
                if ctx.options.scripts.count(s) > 1:
                    raise exceptions.OptionsError("Duplicate script: %s" % s)

            for a in self.addons[:]:
                if a.path not in ctx.options.scripts:
                    ctx.log.info("Un-loading script: %s" % a.name)
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
                    sc = Script(s)
                    ordered.append(sc)
                    newscripts.append(sc)

            self.addons = ordered

            for s in newscripts:
                ctx.master.addons.register(s)
                if self.is_running:
                    # If we're already running, we configure and tell the addon
                    # we're up and running.
                    ctx.master.addons.invoke_addon(s, "running")
