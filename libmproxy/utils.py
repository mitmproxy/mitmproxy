from __future__ import absolute_import
import os
import datetime
import urllib
import re
import time
import functools
import cgi
import json


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
        if i < 9:
            return True
        elif i > 13 and i < 32:
            return True
        elif i > 126:
            return True
    return False


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
    return json.dumps(p, sort_keys=True, indent=4).split("\n")


def urldecode(s):
    """
        Takes a urlencoded string and returns a list of (key, value) tuples.
    """
    return cgi.parse_qsl(s, keep_blank_values=True)


def urlencode(s):
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
    """
    s = [tuple(i) for i in s]
    return urllib.urlencode(s, False)


def multipartdecode(hdrs, content):
    """
        Takes a multipart boundary encoded string and returns list of (key, value) tuples.
    """
    v = hdrs.get_first("content-type")
    if v:
        v = parse_content_type(v)
        if not v:
            return []
        boundary = v[2].get("boundary")
        if not boundary:
            return []

        rx = re.compile(r'\bname="([^"]+)"')
        r = []

        for i in content.split("--" + boundary):
            parts = i.splitlines()
            if len(parts) > 1 and parts[0][0:2] != "--":
                match = rx.search(parts[1])
                if match:
                    key = match.group(1)
                    value = "".join(parts[3 + parts[2:].index(""):])
                    r.append((key, value))
        return r
    return []


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


def parse_content_type(c):
    """
        A simple parser for content-type values. Returns a (type, subtype,
        parameters) tuple, where type and subtype are strings, and parameters
        is a dict. If the string could not be parsed, return None.

        E.g. the following string:

            text/html; charset=UTF-8

        Returns:

            ("text", "html", {"charset": "UTF-8"})
    """
    parts = c.split(";", 1)
    ts = parts[0].split("/", 1)
    if len(ts) != 2:
        return None
    d = {}
    if len(parts) == 2:
        for i in parts[1].split(";"):
            clause = i.split("=", 1)
            if len(clause) == 2:
                d[clause[0].strip()] = clause[1].strip()
    return ts[0].lower(), ts[1].lower(), d


def hostport(scheme, host, port):
    """
        Returns the host component, with a port specifcation if needed.
    """
    if (port, scheme) in [(80, "http"), (443, "https")]:
        return host
    else:
        return "%s:%s" % (host, port)


def unparse_url(scheme, host, port, path=""):
    """
        Returns a URL string, constructed from the specified compnents.
    """
    return "%s://%s%s" % (scheme, hostport(scheme, host, port), path)


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


def safe_subn(pattern, repl, target, *args, **kwargs):
    """
        There are Unicode conversion problems with re.subn. We try to smooth
        that over by casting the pattern and replacement to strings. We really
        need a better solution that is aware of the actual content ecoding.
    """
    return re.subn(str(pattern), str(repl), target, *args, **kwargs)
