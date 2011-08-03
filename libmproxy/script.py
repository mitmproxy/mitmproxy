import imp, os, traceback

class ScriptError(Exception):
    pass

class Context:
    def __init__(self, master, state):
        self.master, self.state = master, state

    def log(self, *args, **kwargs):
        self.master.log(*args, **kwargs)


class Script:
    """
        The instantiator should do something along this vein:

            s = Script(path, master)
            s.load()
            s.run("start")
    """
    def __init__(self, path, master):
        self.path = path
        self.ctx = Context(master, master.state)
        self.mod = None
        self.ns = None

    def load(self):
        """
            Loads a module.

            Raises ScriptError on failure, with argument equal to an error
            message that may be a formatted traceback.
        """
        ns = {}
        try:
            self.mod = execfile(os.path.expanduser(self.path), {}, ns)
        except Exception, v:
            raise ScriptError(traceback.format_exc(v))
        self.ns = ns

    def run(self, name, *args, **kwargs):
        """
            Runs a plugin method.

            Returns:

                (True, retval) on success.
                (False, None) on nonexistent method.
                (Fals, (exc, traceback string)) if there was an exception.
        """
        f = self.ns.get(name)
        if f:
            try:
                return (True, f(self.ctx, *args, **kwargs))
            except Exception, v:
                return (False, (v, traceback.format_exc(v)))
        else:
            return (False, None)
