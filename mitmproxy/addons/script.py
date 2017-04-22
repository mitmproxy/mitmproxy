import contextlib
import os
import shlex
import sys
import threading
import traceback
import types

from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy import eventsequence


import watchdog.events
from watchdog.observers import polling


def parse_command(command):
    """
        Returns a (path, args) tuple.
    """
    if not command or not command.strip():
        raise ValueError("Empty script command.")
    # Windows: escape all backslashes in the path.
    if os.name == "nt":  # pragma: no cover
        backslashes = shlex.split(command, posix=False)[0].count("\\")
        command = command.replace("\\", "\\\\", backslashes)
    args = shlex.split(command)  # pragma: no cover
    args[0] = os.path.expanduser(args[0])
    if not os.path.exists(args[0]):
        raise ValueError(
            ("Script file not found: %s.\r\n"
             "If your script path contains spaces, "
             "make sure to wrap it in additional quotes, e.g. -s \"'./foo bar/baz.py' --args\".") %
            args[0])
    elif os.path.isdir(args[0]):
        raise ValueError("Not a file: %s" % args[0])
    return args[0], args[1:]


def cut_traceback(tb, func_name):
    """
    Cut off a traceback at the function with the given name.
    The func_name's frame is excluded.

    Args:
        tb: traceback object, as returned by sys.exc_info()[2]
        func_name: function name

    Returns:
        Reduced traceback.
    """
    tb_orig = tb

    for _, _, fname, _ in traceback.extract_tb(tb):
        tb = tb.tb_next
        if fname == func_name:
            break

    if tb is None:
        # We could not find the method, take the full stack trace.
        # This may happen on some Python interpreters/flavors (e.g. PyInstaller).
        return tb_orig
    else:
        return tb


class StreamLog:
    """
        A class for redirecting output using contextlib.
    """
    def __init__(self, log):
        self.log = log

    def write(self, buf):
        if buf.strip():
            self.log(buf)


@contextlib.contextmanager
def scriptenv(path, args):
    oldargs = sys.argv
    sys.argv = [path] + args
    script_dir = os.path.dirname(os.path.abspath(path))
    sys.path.append(script_dir)
    stdout_replacement = StreamLog(ctx.log.warn)
    try:
        with contextlib.redirect_stdout(stdout_replacement):
            yield
    except SystemExit as v:
        ctx.log.error("Script exited with code %s" % v.code)
    except Exception:
        etype, value, tb = sys.exc_info()
        tb = cut_traceback(tb, "scriptenv").tb_next
        ctx.log.error(
            "Script error: %s" % "".join(
                traceback.format_exception(etype, value, tb)
            )
        )
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
        exec(code, ns)
    return types.SimpleNamespace(**ns)


class ReloadHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def filter(self, event):
        """
            Returns True only when .py file is changed
        """
        if event.is_directory:
            return False
        if os.path.basename(event.src_path).startswith("."):
            return False
        if event.src_path.endswith(".py"):
            return True
        return False

    def on_modified(self, event):
        if self.filter(event):
            self.callback()

    def on_created(self, event):
        if self.filter(event):
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
        self.dead = False

        self.last_options = None
        self.should_reload = threading.Event()

        for i in eventsequence.Events:
            if not hasattr(self, i):
                def mkprox():
                    evt = i

                    def prox(*args, **kwargs):
                        self.run(evt, *args, **kwargs)
                    return prox
                setattr(self, i, mkprox())

    def run(self, name, *args, **kwargs):
        # It's possible for ns to be un-initialised if we failed during
        # configure
        if self.ns is not None and not self.dead:
            func = getattr(self.ns, name, None)
            if func:
                with scriptenv(self.path, self.args):
                    return func(*args, **kwargs)

    def reload(self):
        self.should_reload.set()

    def load_script(self):
        self.ns = load_script(self.path, self.args)
        l = addonmanager.Loader(ctx.master)
        self.run("load", l)
        if l.boot_into_addon:
            self.ns = l.boot_into_addon

    def tick(self):
        if self.should_reload.is_set():
            self.should_reload.clear()
            ctx.log.info("Reloading script: %s" % self.name)
            self.ns = load_script(self.path, self.args)
            self.configure(self.last_options, self.last_options.keys())
        else:
            self.run("tick")

    def load(self, l):
        self.last_options = ctx.master.options
        self.load_script()

    def configure(self, options, updated):
        self.last_options = options
        if not self.observer:
            self.observer = polling.PollingObserver()
            # Bind the handler to the real underlying master object
            self.observer.schedule(
                ReloadHandler(self.reload),
                os.path.dirname(self.path) or "."
            )
            self.observer.start()
        self.run("configure", options, updated)

    def done(self):
        self.run("done")
        self.dead = True


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
        try:
            sc = Script(command)
        except ValueError as e:
            raise ValueError(str(e))
        sc.load_script()
        for f in flows:
            for evt, o in eventsequence.iterate(f):
                sc.run(evt, o)
        sc.done()
        return sc

    def configure(self, options, updated):
        if "scripts" in updated:
            for s in options.scripts:
                if options.scripts.count(s) > 1:
                    raise exceptions.OptionsError("Duplicate script: %s" % s)

            for a in self.addons:
                if a.name not in options.scripts:
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
                current[a.name] = a

            ordered = []
            newscripts = []
            for s in options.scripts:
                if s in current:
                    ordered.append(current[s])
                else:
                    ctx.log.info("Loading script: %s" % s)
                    try:
                        sc = Script(s)
                    except ValueError as e:
                        raise exceptions.OptionsError(str(e))
                    ordered.append(sc)
                    newscripts.append(sc)

            self.addons = ordered

            for s in newscripts:
                ctx.master.addons.register(s)
                if self.is_running:
                    # If we're already running, we configure and tell the addon
                    # we're up and running.
                    ctx.master.addons.invoke_addon(
                        s, "configure", options, options.keys()
                    )
                    ctx.master.addons.invoke_addon(s, "running")
