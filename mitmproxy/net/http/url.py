from __future__ import annotations

import re
import urllib.parse
from collections.abc import Sequence
from typing import AnyStr
from typing import overload

from mitmproxy.net import check
from mitmproxy.net.check import is_valid_host
from mitmproxy.net.check import is_valid_port
from mitmproxy.utils.strutils import always_str

# This regex extracts & splits the host header into host and port.
# Handles the edge case of IPv6 addresses containing colons.
# https://bugzilla.mozilla.org/show_bug.cgi?id=45891

_authority_re = re.compile(r"^(?P<host>[^:]+|\[.+\])(?::(?P<port>\d+))?$")


def parse(url: str | bytes) -> tuple[bytes, bytes, int, bytes]:
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
    # FIXME: We shouldn't rely on urllib here.

    # Size of Ascii character after encoding is 1 byte which is same as its size
    # But non-Ascii character's size after encoding will be more than its size
    def ascii_check(x):
        if len(x) == len(str(x).encode()):
            return True
        return False

    if isinstance(url, bytes):
        url = url.decode()
        if not ascii_check(url):
            url = urllib.parse.urlsplit(url)  # type: ignore
            url = list(url)  # type: ignore
            url[3] = urllib.parse.quote(url[3])  # type: ignore
            url = urllib.parse.urlunsplit(url)  # type: ignore

    parsed: urllib.parse.ParseResult = urllib.parse.urlparse(url)
    if not parsed.hostname:
        raise ValueError("No hostname given")
    else:
        host = parsed.hostname.encode("idna")

    parsed_b: urllib.parse.ParseResultBytes = parsed.encode("ascii")  # type: ignore

    port = parsed_b.port
    if not port:
        port = 443 if parsed_b.scheme == b"https" else 80

    full_path: bytes = urllib.parse.urlunparse(
        (b"", b"", parsed_b.path, parsed_b.params, parsed_b.query, parsed_b.fragment)  # type: ignore
    )
    if not full_path.startswith(b"/"):
        full_path = b"/" + full_path  # type: ignore

    if not check.is_valid_host(host):
        raise ValueError("Invalid Host")

    return parsed_b.scheme, host, port, full_path


@overload
def unparse(scheme: str, host: str, port: int, path) -> str: ...


@overload
def unparse(scheme: bytes, host: bytes, port: int, path) -> bytes: ...


def unparse(scheme, host, port, path):
    """
    Returns a URL string, constructed from the specified components.
    """
    authority = hostport(scheme, host, port)

    if isinstance(scheme, str):
        return f"{scheme}://{authority}{path}"
    else:
        return b"%s://%s%s" % (scheme, authority, path)


def encode(s: Sequence[tuple[str, str]], similar_to: str | None = None) -> str:
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
        if encoded[-1] == "=":
            encoded = encoded[:-1]

    return encoded


def decode(s):
    """
    Takes a urlencoded string and returns a list of surrogate-escaped (key, value) tuples.
    """
    return urllib.parse.parse_qsl(s, keep_blank_values=True, errors="surrogateescape")


def quote(b: str, safe: str = "/") -> str:
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


def hostport(scheme: AnyStr, host: AnyStr, port: int) -> AnyStr:
    """
    Returns the host component, with a port specification if needed.
    """
    if default_port(scheme) == port:
        return host
    else:
        if isinstance(host, bytes):
            return b"%s:%d" % (host, port)
        else:
            return "%s:%d" % (host, port)


def default_port(scheme: AnyStr) -> int | None:
    return {
        "http": 80,
        b"http": 80,
        "https": 443,
        b"https": 443,
    }.get(scheme, None)


def parse_authority(authority: AnyStr, check: bool) -> tuple[str, int | None]:
    """Extract the host and port from host header/authority information

    Raises:
        ValueError, if check is True and the authority information is malformed.
    """
    try:
        if isinstance(authority, bytes):
            m = _authority_re.match(authority.decode("utf-8"))
            if not m:
                raise ValueError
            host = m["host"].encode("utf-8").decode("idna")
        else:
            m = _authority_re.match(authority)
            if not m:
                raise ValueError
            host = m.group("host")

        if host.startswith("[") and host.endswith("]"):
            host = host[1:-1]
        if not is_valid_host(host):
            raise ValueError

        if m.group("port"):
            port = int(m.group("port"))
            if not is_valid_port(port):
                raise ValueError
            return host, port
        else:
            return host, None

    except ValueError:
        if check:
            raise
        else:
            return always_str(authority, "utf-8", "surrogateescape"), None
