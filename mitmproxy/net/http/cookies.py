import email.utils
import re
import time
from typing import Tuple, List, Iterable

from mitmproxy.coretypes import multidict

"""
A flexible module for cookie parsing and manipulation.

This module differs from usual standards-compliant cookie modules in a number
of ways. We try to be as permissive as possible, and to retain even mal-formed
information. Duplicate cookies are preserved in parsing, and can be set in
formatting. We do attempt to escape and quote values where needed, but will not
reject data that violate the specs.

Parsing accepts the formats in RFC6265 and partially RFC2109 and RFC2965. We
also parse the comma-separated variant of Set-Cookie that allows multiple
cookies to be set in a single header. Serialization follows RFC6265.

    http://tools.ietf.org/html/rfc6265
    http://tools.ietf.org/html/rfc2109
    http://tools.ietf.org/html/rfc2965
"""

_cookie_params = {'expires', 'path', 'comment', 'max-age', 'secure', 'httponly', 'version'}

ESCAPE = re.compile(r"([\"\\])")


class CookieAttrs(multidict.MultiDict):
    @staticmethod
    def _kconv(key):
        return key.lower()

    @staticmethod
    def _reduce_values(values):
        # See the StickyCookieTest for a weird cookie that only makes sense
        # if we take the last part.
        return values[-1]


TSetCookie = Tuple[str, str, CookieAttrs]
TPairs = List[List[str]]  # TODO: Should be List[Tuple[str,str]]?


def _read_until(s, start, term):
    """
        Read until one of the characters in term is reached.
    """
    if start == len(s):
        return "", start + 1
    for i in range(start, len(s)):
        if s[i] in term:
            return s[start:i], i
    return s[start:i + 1], i + 1


def _read_quoted_string(s, start):
    """
        start: offset to the first quote of the string to be read

        A sort of loose super-set of the various quoted string specifications.

        RFC6265 disallows backslashes or double quotes within quoted strings.
        Prior RFCs use backslashes to escape. This leaves us free to apply
        backslash escaping by default and be compatible with everything.
    """
    escaping = False
    ret = []
    # Skip the first quote
    i = start  # initialize in case the loop doesn't run.
    for i in range(start + 1, len(s)):
        if escaping:
            ret.append(s[i])
            escaping = False
        elif s[i] == '"':
            break
        elif s[i] == "\\":
            escaping = True
        else:
            ret.append(s[i])
    return "".join(ret), i + 1


def _read_key(s, start, delims=";="):
    """
        Read a key - the LHS of a token/value pair in a cookie.
    """
    return _read_until(s, start, delims)


def _read_value(s, start, delims):
    """
        Reads a value - the RHS of a token/value pair in a cookie.
    """
    if start >= len(s):
        return "", start
    elif s[start] == '"':
        return _read_quoted_string(s, start)
    else:
        return _read_until(s, start, delims)


def _read_cookie_pairs(s, off=0):
    """
        Read pairs of lhs=rhs values from Cookie headers.

        off: start offset
    """
    pairs = []

    while True:
        lhs, off = _read_key(s, off)
        lhs = lhs.lstrip()

        rhs = ""
        if off < len(s) and s[off] == "=":
            rhs, off = _read_value(s, off + 1, ";")
        if rhs or lhs:
            pairs.append([lhs, rhs])

        off += 1

        if not off < len(s):
            break

    return pairs, off


def _read_set_cookie_pairs(s: str, off=0) -> Tuple[List[TPairs], int]:
    """
        Read pairs of lhs=rhs values from SetCookie headers while handling multiple cookies.

        off: start offset
        specials: attributes that are treated specially
    """
    cookies: List[TPairs] = []
    pairs: TPairs = []

    while True:
        lhs, off = _read_key(s, off, ";=,")
        lhs = lhs.lstrip()

        rhs = ""
        if off < len(s) and s[off] == "=":
            rhs, off = _read_value(s, off + 1, ";,")

            # Special handling of attributes
            if lhs.lower() == "expires":
                # 'expires' values can contain commas in them so they need to
                # be handled separately.

                # We actually bank on the fact that the expires value WILL
                # contain a comma. Things will fail, if they don't.

                # '3' is just a heuristic we use to determine whether we've
                # only read a part of the expires value and we should read more.
                if len(rhs) <= 3:
                    trail, off = _read_value(s, off + 1, ";,")
                    rhs = rhs + "," + trail

            # as long as there's a "=", we consider it a pair
            pairs.append([lhs, rhs])

        elif lhs:
            pairs.append([lhs, rhs])

        # comma marks the beginning of a new cookie
        if off < len(s) and s[off] == ",":
            cookies.append(pairs)
            pairs = []

        off += 1

        if not off < len(s):
            break

    if pairs or not cookies:
        cookies.append(pairs)

    return cookies, off


def _has_special(s: str) -> bool:
    for i in s:
        if i in '",;\\':
            return True
        o = ord(i)
        if o < 0x21 or o > 0x7e:
            return True
    return False


def _format_pairs(pairs, specials=(), sep="; "):
    """
        specials: A lower-cased list of keys that will not be quoted.
    """
    vals = []
    for k, v in pairs:
        if k.lower() not in specials and _has_special(v):
            v = ESCAPE.sub(r"\\\1", v)
            v = '"%s"' % v
        vals.append(f"{k}={v}")
    return sep.join(vals)


def _format_set_cookie_pairs(lst):
    return _format_pairs(
        lst,
        specials=("expires", "path")
    )


def parse_cookie_header(line):
    """
        Parse a Cookie header value.
        Returns a list of (lhs, rhs) tuples.
    """
    pairs, off_ = _read_cookie_pairs(line)
    return pairs


def parse_cookie_headers(cookie_headers):
    cookie_list = []
    for header in cookie_headers:
        cookie_list.extend(parse_cookie_header(header))
    return cookie_list


def format_cookie_header(lst):
    """
        Formats a Cookie header value.
    """
    return _format_pairs(lst)


def parse_set_cookie_header(line: str) -> List[TSetCookie]:
    """
    Parse a Set-Cookie header value

    Returns:
        A list of (name, value, attrs) tuples, where attrs is a
        CookieAttrs dict of attributes. No attempt is made to parse attribute
        values - they are treated purely as strings.
    """
    cookie_pairs, off = _read_set_cookie_pairs(line)
    cookies = []
    for pairs in cookie_pairs:
        if pairs:
            cookie, *attrs = pairs
            cookies.append((
                cookie[0],
                cookie[1],
                CookieAttrs(attrs)
            ))
    return cookies


def parse_set_cookie_headers(headers: Iterable[str]) -> List[TSetCookie]:
    rv = []
    for header in headers:
        cookies = parse_set_cookie_header(header)
        rv.extend(cookies)
    return rv


def format_set_cookie_header(set_cookies: List[TSetCookie]) -> str:
    """
        Formats a Set-Cookie header value.
    """

    rv = []

    for name, value, attrs in set_cookies:

        pairs = [(name, value)]
        pairs.extend(
            attrs.fields if hasattr(attrs, "fields") else attrs
        )

        rv.append(_format_set_cookie_pairs(pairs))

    return ", ".join(rv)


def refresh_set_cookie_header(c: str, delta: int) -> str:
    """
    Args:
        c: A Set-Cookie string
        delta: Time delta in seconds
    Returns:
        A refreshed Set-Cookie string
    Raises:
        ValueError, if the cookie is invalid.
    """
    cookies = parse_set_cookie_header(c)
    for cookie in cookies:
        name, value, attrs = cookie
        if not name or not value:
            raise ValueError("Invalid Cookie")

        if "expires" in attrs:
            e = email.utils.parsedate_tz(attrs["expires"])
            if e:
                f = email.utils.mktime_tz(e) + delta
                attrs.set_all("expires", [email.utils.formatdate(f, usegmt=True)])
            else:
                # This can happen when the expires tag is invalid.
                # reddit.com sends a an expires tag like this: "Thu, 31 Dec
                # 2037 23:59:59 GMT", which is valid RFC 1123, but not
                # strictly correct according to the cookie spec. Browsers
                # appear to parse this tolerantly - maybe we should too.
                # For now, we just ignore this.
                del attrs["expires"]
    return format_set_cookie_header(cookies)


def get_expiration_ts(cookie_attrs):
    """
        Determines the time when the cookie will be expired.

        Considering both 'expires' and 'max-age' parameters.

        Returns: timestamp of when the cookie will expire.
                 None, if no expiration time is set.
    """
    if 'expires' in cookie_attrs:
        e = email.utils.parsedate_tz(cookie_attrs["expires"])
        if e:
            return email.utils.mktime_tz(e)

    elif 'max-age' in cookie_attrs:
        try:
            max_age = int(cookie_attrs['Max-Age'])
        except ValueError:
            pass
        else:
            now_ts = time.time()
            return now_ts + max_age

    return None


def is_expired(cookie_attrs):
    """
        Determines whether a cookie has expired.

        Returns: boolean
    """

    exp_ts = get_expiration_ts(cookie_attrs)
    now_ts = time.time()

    # If no expiration information was provided with the cookie
    if exp_ts is None:
        return False
    else:
        return exp_ts <= now_ts


def group_cookies(pairs):
    """
    Converts a list of pairs to a (name, value, attrs) for each cookie.
    """

    if not pairs:
        return []

    cookie_list = []

    # First pair is always a new cookie
    name, value = pairs[0]
    attrs = []

    for k, v in pairs[1:]:
        if k.lower() in _cookie_params:
            attrs.append((k, v))
        else:
            cookie_list.append((name, value, CookieAttrs(attrs)))
            name, value, attrs = k, v, []

    cookie_list.append((name, value, CookieAttrs(attrs)))
    return cookie_list
