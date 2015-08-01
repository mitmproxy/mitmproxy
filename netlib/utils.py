from __future__ import (absolute_import, print_function, division)
import os.path
import cgi
import urllib
import urlparse
import string


def isascii(s):
    try:
        s.decode("ascii")
    except ValueError:
        return False
    return True


# best way to do it in python 2.x
def bytes_to_int(i):
    return int(i.encode('hex'), 16)


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
        elif i in "\n\t" and not fixspacing:
            parts.append(i)
        else:
            parts.append(".")
    return "".join(parts)


def hexdump(s):
    """
        Returns a set of tuples:
            (offset, hex, str)
    """
    parts = []
    for i in range(0, len(s), 16):
        o = "%.10x" % i
        part = s[i:i + 16]
        x = " ".join("%.2x" % ord(i) for i in part)
        if len(part) < 16:
            x += " "
            x += " ".join("  " for i in range(16 - len(part)))
        parts.append(
            (o, x, cleanBin(part, True))
        )
    return parts


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
    if byte & mask:
        return True


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


def pretty_size(size):
    suffixes = [
        ("B", 2 ** 10),
        ("kB", 2 ** 20),
        ("MB", 2 ** 30),
    ]
    for suf, lim in suffixes:
        if size >= lim:
            continue
        else:
            x = round(size / float(lim / 2 ** 10), 2)
            if x == int(x):
                x = int(x)
            return str(x) + suf


class Data(object):
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




def is_valid_port(port):
    if not 0 <= port <= 65535:
        return False
    return True


def is_valid_host(host):
    try:
        host.decode("idna")
    except ValueError:
        return False
    if "\0" in host:
        return None
    return True


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.

        Checks that:
            port is an integer 0-65535
            host is a valid IDNA-encoded hostname with no null-bytes
            path is valid ASCII
    """
    try:
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    except ValueError:
        return None
    if not scheme:
        return None
    if '@' in netloc:
        # FIXME: Consider what to do with the discarded credentials here Most
        # probably we should extend the signature to return these as a separate
        # value.
        _, netloc = string.rsplit(netloc, '@', maxsplit=1)
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
    if not is_valid_host(host):
        return None
    if not isascii(path):
        return None
    if not is_valid_port(port):
        return None
    return scheme, host, port, path


def get_header_tokens(headers, key):
    """
        Retrieve all tokens for a header key. A number of different headers
        follow a pattern where each header line can containe comma-separated
        tokens, and headers can be set multiple times.
    """
    toks = []
    for i in headers[key]:
        for j in i.split(","):
            toks.append(j.strip())
    return toks


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


def urlencode(s):
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
    """
    s = [tuple(i) for i in s]
    return urllib.urlencode(s, False)

def urldecode(s):
    """
        Takes a urlencoded string and returns a list of (key, value) tuples.
    """
    return cgi.parse_qsl(s, keep_blank_values=True)
