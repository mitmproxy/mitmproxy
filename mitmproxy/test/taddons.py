import contextlib
import sys

import mitmproxy.master
import mitmproxy.options
from mitmproxy import addonmanager
from mitmproxy import command
from mitmproxy import eventsequence
from mitmproxy.addons import script


class TestAddons(addonmanager.AddonManager):
    def __init__(self, master):
        super().__init__(master)

    def trigger(self, event, *args, **kwargs):
        if event == "log":
            self.master.logs.append(args[0])
        elif event == "tick" and not args and not kwargs:
            pass
        else:
            self.master.events.append((event, args, kwargs))
        super().trigger(event, *args, **kwargs)


class RecordingMaster(mitmproxy.master.Master):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addons = TestAddons(self)
        self.events = []
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

    def has_event(self, name):
        for i in self.events:
            if i[0] == name:
                return True
        return False

    def clear(self):
        self.logs = []


class context:
    """
        A context for testing addons, which sets up the mitmproxy.ctx module so
        handlers can run as they would within mitmproxy. The context also
        provides a number of helper methods for common testing scenarios.
    """

    def __init__(self, *addons, options=None):
        options = options or mitmproxy.options.Options()
        self.master = RecordingMaster(
            options
        )
        self.options = self.master.options
        self.wrapped = None

        for a in addons:
            self.master.addons.register(a)

    def ctx(self):
        """
            Returns a new handler context.
        """
        return self.master.handlecontext()

    def __enter__(self):
        self.wrapped = self.ctx()
        self.wrapped.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.wrapped.__exit__(exc_type, exc_value, traceback)
        self.wrapped = None
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
            self.options.update(**kwargs)
            self.master.addons.invoke_addon(
                addon,
                "configure",
                kwargs.keys()
            )

    def script(self, path):
        """
            Loads a script from path, and returns the enclosed addon.
        """
        sc = script.Script(path)
        loader = addonmanager.Loader(self.master)
        self.master.addons.invoke_addon(sc, "load", loader)
        self.configure(sc)
        self.master.addons.invoke_addon(sc, "tick")
        return sc.addons[0] if sc.addons else None

    def invoke(self, addon, event, *args, **kwargs):
        """
            Recursively invoke an event on an addon and all its children.
        """
        return self.master.addons.invoke_addon(addon, event, *args, **kwargs)

    def command(self, func, *args):
        """
            Invoke a command function with a list of string arguments within a command context, mimicing the actual command environment.
        """
        cmd = command.Command(self.master.commands, "test.command", func)
        return cmd.call(args)
