import imp, os, traceback


class Context:
    def __init__(self, master, state):
        self.master, self.state = master, state

    def log(self, *args, **kwargs):
        self.master.log(*args, **kwargs)


class Plugin:
    def __init__(self, path, master):
        self.path = path
        self.ctx = Context(master, master.state)
        self.mod = None
        self.ns = None
        self.load()

    def load(self):
        """
            Loads a module and runs the start method.
        """
        ns = {}
        self.mod = execfile(os.path.expanduser(self.path), {}, ns)
        self.ns = ns
        self.run("start")

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
