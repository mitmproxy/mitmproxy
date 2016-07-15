from __future__ import absolute_import, print_function, division

import contextlib
import os
import shlex
import sys
import threading
import traceback

from mitmproxy import exceptions
from mitmproxy import controller
from mitmproxy import ctx


import watchdog.events
from watchdog.observers import polling


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
            tb = tb.tb_next
            if not os.path.abspath(s[0]).startswith(scriptdir):
                break
        ctx.log.error("Script error: %s" % "".join(traceback.format_tb(tb)))
    finally:
        sys.argv = oldargs
        sys.path.pop()


def load_script(path, args):
    with open(path, "rb") as f:
        try:
            code = compile(f.read(), path, 'exec')
        except SyntaxError as e:
            ctx.log.error(
                "Script error: %s line %s: %s" % (
                    e.filename, e.lineno, e.msg
                )
            )
            return
    ns = {'__file__': os.path.abspath(path)}
    with scriptenv(path, args):
        exec(code, ns, ns)
    return ns


class ReloadHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        self.callback()

    def on_created(self, event):
        self.callback()


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

        self.last_options = None
        self.should_reload = threading.Event()

        for i in controller.Events - set(["start", "configure", "tick"]):
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

    def reload(self):
        self.should_reload.set()

    def tick(self):
        if self.should_reload.is_set():
            self.should_reload.clear()
            ctx.log.info("Reloading script: %s" % self.name)
            self.ns = load_script(self.path, self.args)
            self.configure(self.last_options)
        else:
            self.run("tick")

    def start(self):
        self.ns = load_script(self.path, self.args)
        self.run("start")

    def configure(self, options):
        self.last_options = options
        if not self.observer:
            self.observer = polling.PollingObserver()
            # Bind the handler to the real underlying master object
            self.observer.schedule(
                ReloadHandler(self.reload),
                os.path.dirname(self.path) or "."
            )
            self.observer.start()
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
