# Copyright (C) 2010  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import os, datetime, urlparse, string, urllib
import time, functools, cgi
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


def cleanBin(s, fixspacing=False):
    """
        Cleans binary data to make it safe to display. If fixspacing is True,
        tabs, newlines and so forth will be maintained, if not, they will be
        replaced with a placeholder.
    """
    parts = []
    for i in s:
        o = ord(i)
        if (o > 31 and o < 127):
            parts.append(i)
        elif i in "\n\r\t" and not fixspacing:
            parts.append(i)
        else:
            parts.append(".")
    return "".join(parts)


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
    return cgi.parse_qsl(s)


def urlencode(s):
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
    """
    s = [tuple(i) for i in s]
    return urllib.urlencode(s, False)


def hexdump(s):
    """
        Returns a set of typles:
            (offset, hex, str)
    """
    parts = []
    for i in range(0, len(s), 16):
        o = "%.10x"%i
        part = s[i:i+16]
        x = " ".join("%.2x"%ord(i) for i in part)
        if len(part) < 16:
            x += " "
            x += " ".join("  " for i in range(16 - len(part)))
        parts.append(
            (o, x, cleanBin(part, True))
        )
    return parts


def del_all(dict, keys):
    for key in keys:
        if key in dict:
            del dict[key]


def pretty_size(size):
    suffixes = [
        ("B",   2**10),
        ("kB",   2**20),
        ("M",   2**30),
    ]
    for suf, lim in suffixes:
        if size >= lim:
            continue
        else:
            x = round(size/float(lim/2**10), 2)
            if x == int(x):
                x = int(x)
            return str(x) + suf


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
pkg_data = Data(__name__)


class LRUCache:
    """
        A decorator that implements a self-expiring LRU cache for class
        methods (not functions!).

        Cache data is tracked as attributes on the object itself. There is
        therefore a separate cache for each object instance.
    """
    def __init__(self, size=100):
        self.size = size

    def __call__(self, f):
        cacheName = "_cached_%s"%f.__name__
        cacheListName = "_cachelist_%s"%f.__name__
        size = self.size

        @functools.wraps(f)
        def wrap(self, *args):
            if not hasattr(self, cacheName):
                setattr(self, cacheName, {})
                setattr(self, cacheListName, [])
            cache = getattr(self, cacheName)
            cacheList = getattr(self, cacheListName)
            if cache.has_key(args):
                cacheList.remove(args)
                cacheList.insert(0, args)
                return cache[args]
            else:
                ret = f(self, *args)
                cacheList.insert(0, args)
                cache[args] = ret
                if len(cacheList) > size:
                    d = cacheList.pop()
                    cache.pop(d)
                return ret
        return wrap


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.
    """
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    if not scheme:
        return None
    if ':' in netloc:
        host, port = string.rsplit(netloc, ':', maxsplit=1)
        try:
            port = int(port)
        except ValueError:
            return None
    else:
        host = netloc
        if scheme == "https":
            port = 443
        else:
            port = 80
    path = urlparse.urlunparse(('', '', path, params, query, fragment))
    if not path.startswith("/"):
        path = "/" + path
    return scheme, host, port, path


def parse_proxy_spec(url):
    p = parse_url(url)
    if not p or not p[1]:
        return None
    return p[:3]


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
        return "%s:%s"%(host, port)


def unparse_url(scheme, host, port, path=""):
    """
        Returns a URL string, constructed from the specified compnents.
    """
    return "%s://%s%s"%(scheme, hostport(scheme, host, port), path)


def clean_hanging_newline(t):
    """
        Many editors will silently add a newline to the final line of a
        document (I'm looking at you, Vim). This function fixes this common
        problem at the risk of removing a hanging newline in the rare cases
        where the user actually intends it.
    """
    if t[-1] == "\n":
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
        raise ValueError("Invalid size specification: %s"%s)
