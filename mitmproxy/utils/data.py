import importlib
import inspect
import os.path


class Data:
    def __init__(self, name):
        self.name = name
        m = importlib.import_module(name)
        f = inspect.getsourcefile(m)
        assert f is not None
        dirname = os.path.dirname(f)
        self.dirname = os.path.abspath(dirname)

    def push(self, subpath):
        """
        Change the data object to a path relative to the module.
        """
        dirname = os.path.normpath(os.path.join(self.dirname, subpath))
        ret = Data(self.name)
        ret.dirname = dirname
        return ret

    def path(self, path):
        """
        Returns a path to the package data housed at 'path' under this
        module.Path can be a path to a file, or to a directory.

        This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.normpath(os.path.join(self.dirname, path))
        if not os.path.exists(fullpath):
            raise ValueError("dataPath: %s does not exist." % fullpath)
        return fullpath


pkg_data = Data(__name__).push("..")
