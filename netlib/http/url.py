import six
from six.moves import urllib

from netlib import utils


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


def parse(url):
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

    if not utils.is_valid_host(host):
        raise ValueError("Invalid Host")
    if not utils.is_valid_port(port):
        raise ValueError("Invalid Port")

    return parsed.scheme, host, port, full_path


def unparse(scheme, host, port, path=""):
    """
    Returns a URL string, constructed from the specified components.

    Args:
        All args must be str.
    """
    if path == "*":
        path = ""
    return "%s://%s%s" % (scheme, hostport(scheme, host, port), path)


def encode(s):
    # type: Sequence[Tuple[str,str]] -> str
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
    """
    if six.PY2:
        return urllib.parse.urlencode(s, False)
    else:
        return urllib.parse.urlencode(s, False, errors="surrogateescape")


def decode(s):
    """
        Takes a urlencoded string and returns a list of surrogate-escaped (key, value) tuples.
    """
    if six.PY2:
        return urllib.parse.parse_qsl(s, keep_blank_values=True)
    else:
        return urllib.parse.parse_qsl(s, keep_blank_values=True, errors='surrogateescape')


def quote(b, safe="/"):
    """
    Returns:
        An ascii-encodable str.
    """
    # type: (str) -> str
    if six.PY2:
        return urllib.parse.quote(b, safe=safe)
    else:
        return urllib.parse.quote(b, safe=safe, errors="surrogateescape")


def unquote(s):
    """
    Args:
        s: A surrogate-escaped str
    Returns:
        A surrogate-escaped str
    """
    # type: (str) -> str

    if six.PY2:
        return urllib.parse.unquote(s)
    else:
        return urllib.parse.unquote(s, errors="surrogateescape")


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
