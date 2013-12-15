import os, traceback, threading
import controller

class ScriptError(Exception):
    pass


class Script:
    """
        The instantiator should do something along this vein:

            s = Script(argv, master)
            s.load()
    """
    def __init__(self, argv, ctx):
        self.argv = argv
        self.ctx = ctx
        self.ns = None

    def load(self):
        """
            Loads a module.

            Raises ScriptError on failure, with argument equal to an error
            message that may be a formatted traceback.
        """
        path = os.path.expanduser(self.argv[0])
        if not os.path.exists(path):
            raise ScriptError("No such file: %s" % path)
        if not os.path.isfile(path):
            raise ScriptError("Not a file: %s" % path)
        ns = {}
        try:
            execfile(path, ns, ns)
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
    threading.Thread(target=run).start()


def concurrent(fn):
    if fn.func_name in ["request", "response", "error"]:
        def _concurrent(ctx, flow):
            r = getattr(flow, fn.func_name)
            _handle_concurrent_reply(fn, r, [ctx, flow])
        return _concurrent
    elif fn.func_name in ["clientconnect", "clientdisconnect", "serverconnect"]:
        def _concurrent(ctx, conn):
            _handle_concurrent_reply(fn, conn, [ctx, conn])
        return _concurrent
    raise NotImplementedError("Concurrent decorator not supported for this method.")