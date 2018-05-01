import contextlib
import asyncio
import sys

import mitmproxy.master
import mitmproxy.options
from mitmproxy import addonmanager
from mitmproxy import command
from mitmproxy import eventsequence
from mitmproxy.addons import script, core


class TestAddons(addonmanager.AddonManager):
    def __init__(self, master):
        super().__init__(master)

    def trigger(self, event, *args, **kwargs):
        if event == "log":
            self.master.logs.append(args[0])
        super().trigger(event, *args, **kwargs)


class RecordingMaster(mitmproxy.master.Master):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addons = TestAddons(self)
        self.logs = []

    def dump_log(self, outf=sys.stdout):
        for i in self.logs:
            print("%s: %s" % (i.level, i.msg), file=outf)

    def has_log(self, txt, level=None):
        for i in self.logs:
            if level and i.level != level:
                continue
            if txt.lower() in i.msg.lower():
                return True
        return False

    async def await_log(self, txt, level=None):
        for i in range(20):
            if self.has_log(txt, level):
                return True
            else:
                await asyncio.sleep(0.1)
        return False

    def clear(self):
        self.logs = []


class context:
    """
        A context for testing addons, which sets up the mitmproxy.ctx module so
        handlers can run as they would within mitmproxy. The context also
        provides a number of helper methods for common testing scenarios.
    """

    def __init__(self, *addons, options=None, loadcore=True):
        options = options or mitmproxy.options.Options()
        self.master = RecordingMaster(
            options
        )
        self.options = self.master.options

        if loadcore:
            self.master.addons.add(core.Core())

        for a in addons:
            self.master.addons.add(a)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    @contextlib.contextmanager
    def cycle(self, addon, f):
        """
            Cycles the flow through the events for the flow. Stops if a reply
            is taken (as in flow interception).
        """
        f.reply._state = "start"
        for evt, arg in eventsequence.iterate(f):
            self.master.addons.invoke_addon(
                addon,
                evt,
                arg
            )
            if f.reply.state == "taken":
                return

    def configure(self, addon, **kwargs):
        """
            A helper for testing configure methods. Modifies the registered
            Options object with the given keyword arguments, then calls the
            configure method on the addon with the updated value.
        """
        if addon not in self.master.addons:
            self.master.addons.register(addon)
        with self.options.rollback(kwargs.keys(), reraise=True):
            if kwargs:
                self.options.update(**kwargs)
            else:
                self.master.addons.invoke_addon(addon, "configure", {})

    def script(self, path):
        """
            Loads a script from path, and returns the enclosed addon.
        """
        sc = script.Script(path, False)
        return sc.addons[0] if sc.addons else None

    def invoke(self, addon, event, *args, **kwargs):
        """
            Recursively invoke an event on an addon and all its children.
        """
        return self.master.addons.invoke_addon(addon, event, *args, **kwargs)

    def command(self, func, *args):
        """
            Invoke a command function with a list of string arguments within a command context, mimicking the actual command environment.
        """
        cmd = command.Command(self.master.commands, "test.command", func)
        return cmd.call(args)
