import os, traceback

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
            self.ns = ns
            self.run("start", self.argv)
        except Exception, v:
            raise ScriptError(traceback.format_exc(v))

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
