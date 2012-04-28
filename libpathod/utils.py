import copy, os

class Data:
    def __init__(self, name):
        m = __import__(name)
        dirname, _ = os.path.split(m.__file__)
        self.dirname = os.path.abspath(dirname)

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError, "dataPath: %s does not exist."%fullpath
        return fullpath

    def read(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        p = self.path(path)
        return open(p).read()

data = Data(__name__)
