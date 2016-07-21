from __future__ import absolute_import, print_function, division
import os.path
import re
import importlib
import inspect


def setbit(byte, offset, value):
    """
        Set a bit in a byte to 1 if value is truthy, 0 if not.
    """
    if value:
        return byte | (1 << offset)
    else:
        return byte & ~(1 << offset)


def getbit(byte, offset):
    mask = 1 << offset
    return bool(byte & mask)


class BiDi(object):

    """
        A wee utility class for keeping bi-directional mappings, like field
        constants in protocols. Names are attributes on the object, dict-like
        access maps values to names:

        CONST = BiDi(a=1, b=2)
        assert CONST.a == 1
        assert CONST.get_name(1) == "a"
    """

    def __init__(self, **kwargs):
        self.names = kwargs
        self.values = {}
        for k, v in kwargs.items():
            self.values[v] = k
        if len(self.names) != len(self.values):
            raise ValueError("Duplicate values not allowed.")

    def __getattr__(self, k):
        if k in self.names:
            return self.names[k]
        raise AttributeError("No such attribute: %s", k)

    def get_name(self, n, default=None):
        return self.values.get(n, default)


class Data(object):

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


_label_valid = re.compile(b"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)


def is_valid_host(host):
    # type: (bytes) -> bool
    """
        Checks if a hostname is valid.
    """
    try:
        host.decode("idna")
    except ValueError:
        return False
    if len(host) > 255:
        return False
    if host and host[-1:] == b".":
        host = host[:-1]
    return all(_label_valid.match(x) for x in host.split(b"."))


def is_valid_port(port):
    return 0 <= port <= 65535
