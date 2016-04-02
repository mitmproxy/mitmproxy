from __future__ import (absolute_import, print_function, division)
import os
import datetime
import re
import time
import json
import importlib
import inspect

def timestamp():
    """
        Returns a serializable UTC timestamp.
    """
    return time.time()


def format_timestamp(s):
    s = time.localtime(s)
    d = datetime.datetime.fromtimestamp(time.mktime(s))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp_with_milli(s):
    d = datetime.datetime.fromtimestamp(s)
    return d.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def isBin(s):
    """
        Does this string have any non-ASCII characters?
    """
    for i in s:
        i = ord(i)
        if i < 9 or 13 < i < 32 or 126 < i:
            return True
    return False


def isMostlyBin(s):
    s = s[:100]
    return sum(isBin(ch) for ch in s) / len(s) > 0.3


def isXML(s):
    for i in s:
        if i in "\n \t":
            continue
        elif i == "<":
            return True
        else:
            return False


def pretty_json(s):
    try:
        p = json.loads(s)
    except ValueError:
        return None
    return json.dumps(p, sort_keys=True, indent=4)


def pretty_duration(secs):
    formatters = [
        (100, "{:.0f}s"),
        (10, "{:2.1f}s"),
        (1, "{:1.2f}s"),
    ]

    for limit, formatter in formatters:
        if secs >= limit:
            return formatter.format(secs)
    # less than 1 sec
    return "{:.0f}ms".format(secs * 1000)


class Data:

    def __init__(self, name):
        m = importlib.import_module(name)
        dirname = os.path.dirname(inspect.getsourcefile(m))
        self.dirname = os.path.abspath(dirname)

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
pkg_data = Data(__name__)


class LRUCache:

    """
        A simple LRU cache for generated values.
    """

    def __init__(self, size=100):
        self.size = size
        self.cache = {}
        self.cacheList = []

    def get(self, gen, *args):
        """
            gen: A (presumably expensive) generator function. The identity of
            gen is NOT taken into account by the cache.
            *args: A list of immutable arguments, used to establish identiy by
            *the cache, and passed to gen to generate values.
        """
        if args in self.cache:
            self.cacheList.remove(args)
            self.cacheList.insert(0, args)
            return self.cache[args]
        else:
            ret = gen(*args)
            self.cacheList.insert(0, args)
            self.cache[args] = ret
            if len(self.cacheList) > self.size:
                d = self.cacheList.pop()
                self.cache.pop(d)
            return ret


def clean_hanging_newline(t):
    """
        Many editors will silently add a newline to the final line of a
        document (I'm looking at you, Vim). This function fixes this common
        problem at the risk of removing a hanging newline in the rare cases
        where the user actually intends it.
    """
    if t and t[-1] == "\n":
        return t[:-1]
    return t


def parse_size(s):
    """
        Parses a size specification. Valid specifications are:

            123: bytes
            123k: kilobytes
            123m: megabytes
            123g: gigabytes
    """
    if not s:
        return None
    mult = None
    if s[-1].lower() == "k":
        mult = 1024**1
    elif s[-1].lower() == "m":
        mult = 1024**2
    elif s[-1].lower() == "g":
        mult = 1024**3

    if mult:
        s = s[:-1]
    else:
        mult = 1
    try:
        return int(s) * mult
    except ValueError:
        raise ValueError("Invalid size specification: %s" % s)
