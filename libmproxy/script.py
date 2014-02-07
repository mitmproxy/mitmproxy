import os, traceback, threading, shlex
import controller

class ScriptError(Exception):
    pass


class ScriptContext:
    def __init__(self, master):
        self._master = master

    def log(self, *args, **kwargs):
        """
            Logs an event.

            How this is handled depends on the front-end. mitmdump will display
            events if the eventlog flag ("-e") was passed. mitmproxy sends
            output to the eventlog for display ("v" keyboard shortcut).
        """
        self._master.add_event(*args, **kwargs)

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
        self._master.replay_request(f)


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
        args = shlex.split(command, posix=(os.name != "nt"))
        args[0] = os.path.expanduser(args[0])
        if not os.path.exists(args[0]):
            raise ScriptError("Command not found.")
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
        except Exception, v:
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
            except Exception, v:
                return (False, (v, traceback.format_exc(v)))
        else:
            return (False, None)


def _handle_concurrent_reply(fn, o, args=[], kwargs={}):
    reply = o.reply
    o.reply = controller.DummyReply()
    def run():
        fn(*args, **kwargs)
        reply(o)
    threading.Thread(target=run, name="ScriptThread").start()


def concurrent(fn):
    if fn.func_name in ["request", "response", "error"]:
        def _concurrent(ctx, flow):
            r = getattr(flow, fn.func_name)
            _handle_concurrent_reply(fn, r, [ctx, flow])
        return _concurrent
    elif fn.func_name in ["clientconnect", "serverconnect", "clientdisconnect"]:
        def _concurrent(ctx, conn):
            _handle_concurrent_reply(fn, conn, [ctx, conn])
        return _concurrent
    raise NotImplementedError("Concurrent decorator not supported for this method.")
