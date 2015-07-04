from __future__ import absolute_import
import os
import traceback
import threading
import shlex
from . import controller


class ScriptError(Exception):
    pass


class ScriptContext:
    def __init__(self, master):
        self._master = master

    def log(self, message, level="info"):
        """
            Logs an event.

            By default, only events with level "error" get displayed. This can be controlled with the "-v" switch.
            How log messages are handled depends on the front-end. mitmdump will print them to stdout,
            mitmproxy sends output to the eventlog for display ("e" keyboard shortcut).
        """
        self._master.add_event(message, level)

    def kill_flow(self, f):
        """
            Kills a flow immediately. No further data will be sent to the client or the server.
        """
        f.kill(self._master)

    def duplicate_flow(self, f):
        """
            Returns a duplicate of the specified flow. The flow is also
            injected into the current state, and is ready for editing, replay,
            etc.
        """
        self._master.pause_scripts = True
        f = self._master.duplicate_flow(f)
        self._master.pause_scripts = False
        return f

    def replay_request(self, f):
        """
            Replay the request on the current flow. The response will be added
            to the flow object.
        """
        return self._master.replay_request(f, block=True, run_scripthooks=False)

    @property
    def app_registry(self):
        return self._master.apps


class Script:
    """
        The instantiator should do something along this vein:

            s = Script(argv, master)
            s.load()
    """

    def __init__(self, command, master):
        self.command = command
        self.argv = self.parse_command(command)
        self.ctx = ScriptContext(master)
        self.ns = None
        self.load()

    @classmethod
    def parse_command(klass, command):
        if not command or not command.strip():
            raise ScriptError("Empty script command.")
        if os.name == "nt":  # Windows: escape all backslashes in the path.
            backslashes = shlex.split(command, posix=False)[0].count("\\")
            command = command.replace("\\", "\\\\", backslashes)
        args = shlex.split(command)
        args[0] = os.path.expanduser(args[0])
        if not os.path.exists(args[0]):
            raise ScriptError(
                ("Script file not found: %s.\r\n"
                 "If your script path contains spaces, "
                 "make sure to wrap it in additional quotes, e.g. -s \"'./foo bar/baz.py' --args\".") %
                args[0])
        elif not os.path.isfile(args[0]):
            raise ScriptError("Not a file: %s" % args[0])
        return args

    def load(self):
        """
            Loads a module.

            Raises ScriptError on failure, with argument equal to an error
            message that may be a formatted traceback.
        """
        ns = {}
        try:
            execfile(self.argv[0], ns, ns)
        except Exception as v:
            raise ScriptError(traceback.format_exc(v))
        self.ns = ns
        r = self.run("start", self.argv)
        if not r[0] and r[1]:
            raise ScriptError(r[1][1])

    def unload(self):
        return self.run("done")

    def run(self, name, *args, **kwargs):
        """
            Runs a plugin method.

            Returns:

                (True, retval) on success.
                (False, None) on nonexistent method.
                (False, (exc, traceback string)) if there was an exception.
        """
        f = self.ns.get(name)
        if f:
            try:
                return (True, f(self.ctx, *args, **kwargs))
            except Exception as v:
                return (False, (v, traceback.format_exc(v)))
        else:
            return (False, None)


class ReplyProxy(object):
    def __init__(self, original_reply, script_thread):
        self.original_reply = original_reply
        self.script_thread = script_thread
        self._ignore_call = True
        self.lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        with self.lock:
            if self._ignore_call:
                self.script_thread.start()
                self._ignore_call = False
                return
        self.original_reply(*args, **kwargs)

    def __getattr__(self, k):
        return getattr(self.original_reply, k)


def _handle_concurrent_reply(fn, o, *args, **kwargs):
    # Make first call to o.reply a no op and start the script thread.
    # We must not start the script thread before, as this may lead to a nasty race condition
    # where the script thread replies a different response before the normal reply, which then gets swallowed.

    def run():
        fn(*args, **kwargs)
        # If the script did not call .reply(), we have to do it now.
        reply_proxy()

    script_thread = ScriptThread(target=run)

    reply_proxy = ReplyProxy(o.reply, script_thread)
    o.reply = reply_proxy


class ScriptThread(threading.Thread):
    name = "ScriptThread"


def concurrent(fn):
    if fn.func_name in (
            "request",
            "response",
            "error",
            "clientconnect",
            "serverconnect",
            "clientdisconnect"):
        def _concurrent(ctx, obj):
            _handle_concurrent_reply(fn, obj, ctx, obj)
        return _concurrent
    raise NotImplementedError(
        "Concurrent decorator not supported for this method.")
