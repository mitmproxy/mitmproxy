import os
import importlib
import time
import sys

from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy import ctx


def load_script(actx, path):
    if not os.path.exists(path):
        ctx.log.info("No such file: %s" % path)
        return
    loader = importlib.machinery.SourceFileLoader(os.path.basename(path), path)
    try:
        oldpath = sys.path
        sys.path.insert(0, os.path.dirname(path))
        with addonmanager.safecall():
            m = loader.load_module()
            if not getattr(m, "name", None):
                m.name = path
            return m
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
        self.ns = None

        self.last_load = 0
        self.last_mtime = 0

    @property
    def addons(self):
        return [self.ns] if self.ns else []

    def tick(self):
        if time.time() - self.last_load > self.ReloadInterval:
            mtime = os.stat(self.path).st_mtime
            if mtime > self.last_mtime:
                ctx.log.info("Loading script: %s" % self.name)
                if self.ns:
                    ctx.master.addons.remove(self.ns)
                self.ns = load_script(ctx, self.path)
                if self.ns:
                    # We're already running, so we have to explicitly register and
                    # configure the addon
                    ctx.master.addons.register(self.ns)
                    ctx.master.addons.invoke_addon(self.ns, "running")
                    ctx.master.addons.invoke_addon(
                        self.ns,
                        "configure",
                        ctx.options,
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

    def run_once(self, command, flows):
        # Returning once we have proper commands
        raise NotImplementedError

    def configure(self, options, updated):
        if "scripts" in updated:
            for s in options.scripts:
                if options.scripts.count(s) > 1:
                    raise exceptions.OptionsError("Duplicate script: %s" % s)

            for a in self.addons[:]:
                if a.path not in options.scripts:
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
            for s in options.scripts:
                if s in current:
                    ordered.append(current[s])
                else:
                    ctx.log.info("Loading script: %s" % s)
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
