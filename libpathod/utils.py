import os, re
import rparse

def get_header(val, headers):
    """
        Header keys may be Values, so we have to "generate" them as we try the match.
    """
    for k, v in headers:
        if len(k) == len(val) and k[:].lower() == val:
            return v
    return None


def parse_anchor_spec(s):
    """
        Return a tuple, or None on error.
    """
    if not "=" in s:
        return None
    return tuple(s.split("=", 1))


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


data = Data(__name__)
