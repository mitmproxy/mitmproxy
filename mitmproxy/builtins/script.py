from __future__ import absolute_import, print_function, division

import contextlib
import os
import shlex
import sys
import traceback
import copy

from mitmproxy import exceptions
from mitmproxy import controller
from mitmproxy import ctx


import watchdog.events
# The OSX reloader in watchdog 0.8.3 breaks when unobserving paths.
# We use the PollingObserver instead.
if sys.platform == 'darwin':  # pragma: no cover
    from watchdog.observers.polling import PollingObserver as Observer
else:
    from watchdog.observers import Observer


def parse_command(command):
    """
        Returns a (path, args) tuple.
    """
    if not command or not command.strip():
        raise exceptions.AddonError("Empty script command.")
    # Windows: escape all backslashes in the path.
    if os.name == "nt":  # pragma: no cover
        backslashes = shlex.split(command, posix=False)[0].count("\\")
        command = command.replace("\\", "\\\\", backslashes)
    args = shlex.split(command)  # pragma: no cover
    args[0] = os.path.expanduser(args[0])
    if not os.path.exists(args[0]):
        raise exceptions.AddonError(
            ("Script file not found: %s.\r\n"
             "If your script path contains spaces, "
             "make sure to wrap it in additional quotes, e.g. -s \"'./foo bar/baz.py' --args\".") %
            args[0])
    elif os.path.isdir(args[0]):
        raise exceptions.AddonError("Not a file: %s" % args[0])
    return args[0], args[1:]


@contextlib.contextmanager
def scriptenv(path, args):
    oldargs = sys.argv
    sys.argv = [path] + args
    script_dir = os.path.dirname(os.path.abspath(path))
    sys.path.append(script_dir)
    try:
        yield
    except Exception:
        _, _, tb = sys.exc_info()
        scriptdir = os.path.dirname(os.path.abspath(path))
        for i, s in enumerate(reversed(traceback.extract_tb(tb))):
            if not os.path.abspath(s[0]).startswith(scriptdir):
                break
            else:
                tb = tb.tb_next
        ctx.log.warn("".join(traceback.format_tb(tb)))
    finally:
        sys.argv = oldargs
        sys.path.pop()


def load_script(path, args):
    ns = {'__file__': os.path.abspath(path)}
    with scriptenv(path, args):
        with open(path, "rb") as f:
            code = compile(f.read(), path, 'exec')
            exec(code, ns, ns)
    return ns


class ReloadHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, callback, master, options):
        self.callback = callback
        self.master, self.options = master, options

    def on_modified(self, event):
        self.callback(self.master, self.options)

    def on_created(self, event):
        self.callback(self.master, self.options)


class Script:
    """
        An addon that manages a single script.
    """
    def __init__(self, command):
        self.name = command

        self.command = command
        self.path, self.args = parse_command(command)
        self.ns = None
        self.observer = None

        for i in controller.Events:
            def mkprox():
                evt = i

                def prox(*args, **kwargs):
                    self.run(evt, *args, **kwargs)
                return prox
            setattr(self, i, mkprox())

    def run(self, name, *args, **kwargs):
        # It's possible for ns to be un-initialised if we failed during
        # configure
        if self.ns is not None:
            func = self.ns.get(name)
            if func:
                with scriptenv(self.path, self.args):
                    func(*args, **kwargs)

    def reload(self, master, options):
        with master.handlecontext(None):
            self.ns = None
            self.configure(options)

    def configure(self, options):
        if not self.observer:
            self.observer = Observer()
            # Bind the handler to the real underlying master object
            self.observer.schedule(
                ReloadHandler(
                    self.reload,
                    ctx.master._getobj(),
                    copy.copy(options),
                ),
                os.path.dirname(self.path) or "."
            )
            self.observer.start()
        if not self.ns:
            self.ns = load_script(self.path, self.args)
        self.run("configure", options)


class ScriptLoader():
    """
        An addon that manages loading scripts from options.
    """
    def configure(self, options):
        for s in options.scripts or []:
            if not ctx.master.addons.has_addon(s):
                ctx.log.info("Loading script: %s" % s)
                sc = Script(s)
                ctx.master.addons.add(sc)
        for a in ctx.master.addons.chain:
            if isinstance(a, Script):
                if a.name not in options.scripts or []:
                    ctx.master.addons.remove(a)
