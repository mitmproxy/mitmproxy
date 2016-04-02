from six.moves import http_cookies as Cookie
import re
from email.utils import parsedate_tz, formatdate, mktime_tz

from .. import odict

"""
A flexible module for cookie parsing and manipulation.

This module differs from usual standards-compliant cookie modules in a number
of ways. We try to be as permissive as possible, and to retain even mal-formed
information. Duplicate cookies are preserved in parsing, and can be set in
formatting. We do attempt to escape and quote values where needed, but will not
reject data that violate the specs.

Parsing accepts the formats in RFC6265 and partially RFC2109 and RFC2965. We do
not parse the comma-separated variant of Set-Cookie that allows multiple
cookies to be set in a single header. Technically this should be feasible, but
it turns out that violations of RFC6265 that makes the parsing problem
indeterminate are much more common than genuine occurences of the multi-cookie
variants. Serialization follows RFC6265.

    http://tools.ietf.org/html/rfc6265
    http://tools.ietf.org/html/rfc2109
    http://tools.ietf.org/html/rfc2965
"""

# TODO: Disallow LHS-only Cookie values


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


def _read_token(s, start):
    """
        Read a token - the LHS of a token/value pair in a cookie.
    """
    return _read_until(s, start, ";=")


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


def _read_value(s, start, delims):
    """
        Reads a value - the RHS of a token/value pair in a cookie.

        special: If the value is special, commas are premitted. Else comma
        terminates. This helps us support old and new style values.
    """
    if start >= len(s):
        return "", start
    elif s[start] == '"':
        return _read_quoted_string(s, start)
    else:
        return _read_until(s, start, delims)


def _read_pairs(s, off=0):
    """
        Read pairs of lhs=rhs values.

        off: start offset
        specials: a lower-cased list of keys that may contain commas
    """
    vals = []
    while True:
        lhs, off = _read_token(s, off)
        lhs = lhs.lstrip()
        if lhs:
            rhs = None
            if off < len(s):
                if s[off] == "=":
                    rhs, off = _read_value(s, off + 1, ";")
            vals.append([lhs, rhs])
        off += 1
        if not off < len(s):
            break
    return vals, off


def _has_special(s):
    for i in s:
        if i in '",;\\':
            return True
        o = ord(i)
        if o < 0x21 or o > 0x7e:
            return True
    return False


ESCAPE = re.compile(r"([\"\\])")


def _format_pairs(lst, specials=(), sep="; "):
    """
        specials: A lower-cased list of keys that will not be quoted.
    """
    vals = []
    for k, v in lst:
        if v is None:
            vals.append(k)
        else:
            if k.lower() not in specials and _has_special(v):
                v = ESCAPE.sub(r"\\\1", v)
                v = '"%s"' % v
            vals.append("%s=%s" % (k, v))
    return sep.join(vals)


def _format_set_cookie_pairs(lst):
    return _format_pairs(
        lst,
        specials=("expires", "path")
    )


def _parse_set_cookie_pairs(s):
    """
        For Set-Cookie, we support multiple cookies as described in RFC2109.
        This function therefore returns a list of lists.
    """
    pairs, off_ = _read_pairs(s)
    return pairs


def parse_set_cookie_header(line):
    """
        Parse a Set-Cookie header value

        Returns a (name, value, attrs) tuple, or None, where attrs is an
        ODictCaseless set of attributes. No attempt is made to parse attribute
        values - they are treated purely as strings.
    """
    pairs = _parse_set_cookie_pairs(line)
    if pairs:
        return pairs[0][0], pairs[0][1], odict.ODictCaseless(pairs[1:])


def format_set_cookie_header(name, value, attrs):
    """
        Formats a Set-Cookie header value.
    """
    pairs = [[name, value]]
    pairs.extend(attrs.lst)
    return _format_set_cookie_pairs(pairs)


def parse_cookie_header(line):
    """
        Parse a Cookie header value.
        Returns a (possibly empty) ODict object.
    """
    pairs, off_ = _read_pairs(line)
    return odict.ODict(pairs)


def format_cookie_header(od):
    """
        Formats a Cookie header value.
    """
    return _format_pairs(od.lst)


def refresh_set_cookie_header(c, delta):
    """
    Args:
        c: A Set-Cookie string
        delta: Time delta in seconds
    Returns:
        A refreshed Set-Cookie string
    """
    try:
        c = Cookie.SimpleCookie(str(c))
    except Cookie.CookieError:
        raise ValueError("Invalid Cookie")
    for i in c.values():
        if "expires" in i:
            d = parsedate_tz(i["expires"])
            if d:
                d = mktime_tz(d) + delta
                i["expires"] = formatdate(d)
            else:
                # This can happen when the expires tag is invalid.
                # reddit.com sends a an expires tag like this: "Thu, 31 Dec
                # 2037 23:59:59 GMT", which is valid RFC 1123, but not
                # strictly correct according to the cookie spec. Browsers
                # appear to parse this tolerantly - maybe we should too.
                # For now, we just ignore this.
                del i["expires"]
    ret = c.output(header="").strip()
    if not ret:
        raise ValueError("Invalid Cookie")
    return ret
