import os.path
import importlib
import inspect


class Data:

    def __init__(self, name):
        m = importlib.import_module(name)
        dirname = os.path.dirname(inspect.getsourcefile(m))
        self.dirname = os.path.abspath(dirname)

    def push(self, subpath):
        """
            Change the data object to a path relative to the module.
        """
        self.dirname = os.path.join(self.dirname, subpath)
        return self

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError("dataPath: %s does not exist." % fullpath)
        return fullpath


pkg_data = Data(__name__).push("..")
