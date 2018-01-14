import urllib.parse
from typing import Sequence
from typing import Tuple

from mitmproxy.net import check


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

    if isinstance(url, bytes):
        host = parsed.hostname

        # this should not raise a ValueError,
        # but we try to be very forgiving here and accept just everything.
    else:
        host = parsed.hostname.encode("idna")
        if isinstance(parsed, urllib.parse.ParseResult):
            parsed = parsed.encode("ascii")

    port = parsed.port  # Returns None if port number invalid in Py3.5. Will throw ValueError in Py3.6
    if not port:
        port = 443 if parsed.scheme == b"https" else 80

    full_path = urllib.parse.urlunparse(
        (b"", b"", parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
    if not full_path.startswith(b"/"):
        full_path = b"/" + full_path

    if not check.is_valid_host(host):
        raise ValueError("Invalid Host")

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


def encode(s: Sequence[Tuple[str, str]], similar_to: str=None) -> str:
    """
        Takes a list of (key, value) tuples and returns a urlencoded string.
        If similar_to is passed, the output is formatted similar to the provided urlencoded string.
    """

    remove_trailing_equal = False
    if similar_to:
        remove_trailing_equal = any("=" not in param for param in similar_to.split("&"))

    encoded = urllib.parse.urlencode(s, False, errors="surrogateescape")

    if encoded and remove_trailing_equal:
        encoded = encoded.replace("=&", "&")
        if encoded[-1] == '=':
            encoded = encoded[:-1]

    return encoded


def decode(s):
    """
        Takes a urlencoded string and returns a list of surrogate-escaped (key, value) tuples.
    """
    return urllib.parse.parse_qsl(s, keep_blank_values=True, errors='surrogateescape')


def quote(b: str, safe: str="/") -> str:
    """
    Returns:
        An ascii-encodable str.
    """
    return urllib.parse.quote(b, safe=safe, errors="surrogateescape")


def unquote(s: str) -> str:
    """
    Args:
        s: A surrogate-escaped str
    Returns:
        A surrogate-escaped str
    """
    return urllib.parse.unquote(s, errors="surrogateescape")


def hostport(scheme, host, port):
    """
        Returns the host component, with a port specifcation if needed.
    """
    if (port, scheme) in [(80, "http"), (443, "https"), (80, b"http"), (443, b"https")]:
        return host
    else:
        if isinstance(host, bytes):
            return b"%s:%d" % (host, port)
        else:
            return "%s:%d" % (host, port)
