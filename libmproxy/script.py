from __future__ import absolute_import
import os
import traceback
import threading
import shlex
import sys


class ScriptError(Exception):
    pass


class ScriptContext:
    """
    The script context should be used to interact with the global mitmproxy state from within a
    script.
    """
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
        Script object representing an inline script.
    """

    def __init__(self, command, master):
        self.args = self.parse_command(command)
        self.ctx = ScriptContext(master)
        self.ns = None
        self.load()

    @classmethod
    def parse_command(cls, command):
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
        elif os.path.isdir(args[0]):
            raise ScriptError("Not a file: %s" % args[0])
        return args

    def load(self):
        """
            Loads an inline script.

            Returns:
                The return value of self.run("start", ...)

            Raises:
                ScriptError on failure
        """
        if self.ns is not None:
            self.unload()
        script_dir = os.path.dirname(os.path.abspath(self.args[0]))
        ns = {'__file__': os.path.abspath(self.args[0])}
        sys.path.append(script_dir)
        try:
            execfile(self.args[0], ns, ns)
        except Exception as e:
            # Python 3: use exception chaining, https://www.python.org/dev/peps/pep-3134/
            raise ScriptError(traceback.format_exc(e))
        sys.path.pop()
        self.ns = ns
        return self.run("start", self.args)

    def unload(self):
        ret = self.run("done")
        self.ns = None
        return ret

    def run(self, name, *args, **kwargs):
        """
            Runs an inline script hook.

            Returns:
                The return value of the method.
                None, if the script does not provide the method.

            Raises:
                ScriptError if there was an exception.
        """
        f = self.ns.get(name)
        if f:
            try:
                return f(self.ctx, *args, **kwargs)
            except Exception as e:
                raise ScriptError(traceback.format_exc(e))
        else:
            return None


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
            "clientdisconnect",
            "next_layer"):
        def _concurrent(ctx, obj):
            _handle_concurrent_reply(fn, obj, ctx, obj)

        return _concurrent
    raise NotImplementedError(
        "Concurrent decorator not supported for '%s' method." % fn.func_name)
