from __future__ import absolute_import, print_function, division
import os.path
import re
import codecs
import unicodedata
from abc import ABCMeta, abstractmethod
import importlib
import inspect

import six

from six.moves import urllib
import hyperframe


@six.add_metaclass(ABCMeta)
class Serializable(object):
    """
    Abstract Base Class that defines an API to save an object's state and restore it later on.
    """

    @classmethod
    @abstractmethod
    def from_state(cls, state):
        """
        Create a new object from the given state.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_state(self):
        """
        Retrieve object state.
        """
        raise NotImplementedError()

    @abstractmethod
    def set_state(self, state):
        """
        Set object state to the given state.
        """
        raise NotImplementedError()

    def copy(self):
        return self.from_state(self.get_state())


def always_bytes(unicode_or_bytes, *encode_args):
    if isinstance(unicode_or_bytes, six.text_type):
        return unicode_or_bytes.encode(*encode_args)
    return unicode_or_bytes


def always_byte_args(*encode_args):
    """Decorator that transparently encodes all arguments passed as unicode"""
    def decorator(fun):
        def _fun(*args, **kwargs):
            args = [always_bytes(arg, *encode_args) for arg in args]
            kwargs = {k: always_bytes(v, *encode_args) for k, v in six.iteritems(kwargs)}
            return fun(*args, **kwargs)
        return _fun
    return decorator


def native(s, *encoding_opts):
    """
    Convert :py:class:`bytes` or :py:class:`unicode` to the native
    :py:class:`str` type, using latin1 encoding if conversion is necessary.

    https://www.python.org/dev/peps/pep-3333/#a-note-on-string-types
    """
    if not isinstance(s, (six.binary_type, six.text_type)):
        raise TypeError("%r is neither bytes nor unicode" % s)
    if six.PY3:
        if isinstance(s, six.binary_type):
            return s.decode(*encoding_opts)
    else:
        if isinstance(s, six.text_type):
            return s.encode(*encoding_opts)
    return s


def isascii(bytes):
    try:
        bytes.decode("ascii")
    except ValueError:
        return False
    return True


def clean_bin(s, keep_spacing=True):
    """
        Cleans binary data to make it safe to display.

        Args:
            keep_spacing: If False, tabs and newlines will also be replaced.
    """
    if isinstance(s, six.text_type):
        if keep_spacing:
            keep = u" \n\r\t"
        else:
            keep = u" "
        return u"".join(
            ch if (unicodedata.category(ch)[0] not in "CZ" or ch in keep) else u"."
            for ch in s
        )
    else:
        if keep_spacing:
            keep = (9, 10, 13)  # \t, \n, \r,
        else:
            keep = ()
        return b"".join(
            six.int2byte(ch) if (31 < ch < 127 or ch in keep) else b"."
            for ch in six.iterbytes(s)
        )


def hexdump(s):
    """
        Returns:
            A generator of (offset, hex, str) tuples
    """
    for i in range(0, len(s), 16):
        offset = "{:0=10x}".format(i).encode()
        part = s[i:i + 16]
        x = b" ".join("{:0=2x}".format(i).encode() for i in six.iterbytes(part))
        x = x.ljust(47)  # 16*2 + 15
        yield (offset, x, clean_bin(part, False))


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


_label_valid = re.compile(b"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)


def is_valid_host(host):
    """
    Checks if a hostname is valid.

    Args:
      host (bytes): The hostname
    """
    try:
        host.decode("idna")
    except ValueError:
        return False
    if len(host) > 255:
        return False
    if host[-1] == b".":
        host = host[:-1]
    return all(_label_valid.match(x) for x in host.split(b"."))


def is_valid_port(port):
    return 0 <= port <= 65535


# PY2 workaround
def decode_parse_result(result, enc):
    if hasattr(result, "decode"):
        return result.decode(enc)
    else:
        return urllib.parse.ParseResult(*[x.decode(enc) for x in result])


# PY2 workaround
def encode_parse_result(result, enc):
    if hasattr(result, "encode"):
        return result.encode(enc)
    else:
        return urllib.parse.ParseResult(*[x.encode(enc) for x in result])


def parse_url(url):
    """
        URL-parsing function that checks that
            - port is an integer 0-65535
            - host is a valid IDNA-encoded hostname with no null-bytes
            - path is valid ASCII

        Args:
            A URL (as bytes or as unicode)

        Returns:
            A (scheme, host, port, path) tuple

        Raises:
            ValueError, if the URL is not properly formatted.
    """
    parsed = urllib.parse.urlparse(url)

    if not parsed.hostname:
        raise ValueError("No hostname given")

    if isinstance(url, six.binary_type):
        host = parsed.hostname

        # this should not raise a ValueError,
        # but we try to be very forgiving here and accept just everything.
        # decode_parse_result(parsed, "ascii")
    else:
        host = parsed.hostname.encode("idna")
        parsed = encode_parse_result(parsed, "ascii")

    port = parsed.port
    if not port:
        port = 443 if parsed.scheme == b"https" else 80

    full_path = urllib.parse.urlunparse(
        (b"", b"", parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
    if not full_path.startswith(b"/"):
        full_path = b"/" + full_path

    if not is_valid_host(host):
        raise ValueError("Invalid Host")
    if not is_valid_port(port):
        raise ValueError("Invalid Port")

    return parsed.scheme, host, port, full_path


def get_header_tokens(headers, key):
    """
        Retrieve all tokens for a header key. A number of different headers
        follow a pattern where each header line can containe comma-separated
        tokens, and headers can be set multiple times.
    """
    if key not in headers:
        return []
    tokens = headers[key].split(",")
    return [token.strip() for token in tokens]


def hostport(scheme, host, port):
    """
        Returns the host component, with a port specifcation if needed.
    """
    if (port, scheme) in [(80, "http"), (443, "https"), (80, b"http"), (443, b"https")]:
        return host
    else:
        if isinstance(host, six.binary_type):
            return b"%s:%d" % (host, port)
        else:
            return "%s:%d" % (host, port)


def unparse_url(scheme, host, port, path=""):
    """
    Returns a URL string, constructed from the specified components.

    Args:
        All args must be str.
    """
    return "%s://%s%s" % (scheme, hostport(scheme, host, port), path)


def urlencode(s):
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
    """
    s = [tuple(i) for i in s]
    return urllib.parse.urlencode(s, False)


def urldecode(s):
    """
        Takes a urlencoded string and returns a list of (key, value) tuples.
    """
    return urllib.parse.parse_qsl(s, keep_blank_values=True)


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


def multipartdecode(headers, content):
    """
        Takes a multipart boundary encoded string and returns list of (key, value) tuples.
    """
    v = headers.get("content-type")
    if v:
        v = parse_content_type(v)
        if not v:
            return []
        try:
            boundary = v[2]["boundary"].encode("ascii")
        except (KeyError, UnicodeError):
            return []

        rx = re.compile(br'\bname="([^"]+)"')
        r = []

        for i in content.split(b"--" + boundary):
            parts = i.splitlines()
            if len(parts) > 1 and parts[0][0:2] != b"--":
                match = rx.search(parts[1])
                if match:
                    key = match.group(1)
                    value = b"".join(parts[3 + parts[2:].index(b""):])
                    r.append((key, value))
        return r
    return []


def http2_read_raw_frame(rfile):
    header = rfile.safe_read(9)
    length = int(codecs.encode(header[:3], 'hex_codec'), 16)

    if length == 4740180:
        raise ValueError("Length field looks more like HTTP/1.1: %s" % rfile.peek(20))

    body = rfile.safe_read(length)
    return [header, body]


def http2_read_frame(rfile):
    header, body = http2_read_raw_frame(rfile)
    frame, length = hyperframe.frame.Frame.parse_frame_header(header)
    frame.parse_body(memoryview(body))
    return frame


def safe_subn(pattern, repl, target, *args, **kwargs):
    """
        There are Unicode conversion problems with re.subn. We try to smooth
        that over by casting the pattern and replacement to strings. We really
        need a better solution that is aware of the actual content ecoding.
    """
    return re.subn(str(pattern), str(repl), target, *args, **kwargs)
