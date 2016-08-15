import collections
import email.utils
import re
import time

from netlib import multidict

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

_cookie_params = set((
    'expires', 'path', 'comment', 'max-age',
    'secure', 'httponly', 'version',
))


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


def parse_set_cookie_headers(headers):
    ret = []
    for header in headers:
        v = parse_set_cookie_header(header)
        if v:
            name, value, attrs = v
            ret.append((name, SetCookie(value, attrs)))
    return ret


class CookieAttrs(multidict.ImmutableMultiDict):
    @staticmethod
    def _kconv(key):
        return key.lower()

    @staticmethod
    def _reduce_values(values):
        # See the StickyCookieTest for a weird cookie that only makes sense
        # if we take the last part.
        return values[-1]


SetCookie = collections.namedtuple("SetCookie", ["value", "attrs"])


def parse_set_cookie_header(line):
    """
        Parse a Set-Cookie header value

        Returns a (name, value, attrs) tuple, or None, where attrs is an
        CookieAttrs dict of attributes. No attempt is made to parse attribute
        values - they are treated purely as strings.
    """
    pairs = _parse_set_cookie_pairs(line)
    if pairs:
        return pairs[0][0], pairs[0][1], CookieAttrs(tuple(x) for x in pairs[1:])


def format_set_cookie_header(name, value, attrs):
    """
        Formats a Set-Cookie header value.
    """
    pairs = [(name, value)]
    pairs.extend(
        attrs.fields if hasattr(attrs, "fields") else attrs
    )
    return _format_set_cookie_pairs(pairs)


def parse_cookie_headers(cookie_headers):
    cookie_list = []
    for header in cookie_headers:
        cookie_list.extend(parse_cookie_header(header))
    return cookie_list


def parse_cookie_header(line):
    """
        Parse a Cookie header value.
        Returns a list of (lhs, rhs) tuples.
    """
    pairs, off_ = _read_pairs(line)
    return pairs


def format_cookie_header(lst):
    """
        Formats a Cookie header value.
    """
    return _format_pairs(lst)


def refresh_set_cookie_header(c, delta):
    """
    Args:
        c: A Set-Cookie string
        delta: Time delta in seconds
    Returns:
        A refreshed Set-Cookie string
    """

    name, value, attrs = parse_set_cookie_header(c)
    if not name or not value:
        raise ValueError("Invalid Cookie")

    if "expires" in attrs:
        e = email.utils.parsedate_tz(attrs["expires"])
        if e:
            f = email.utils.mktime_tz(e) + delta
            attrs = attrs.with_set_all("expires", [email.utils.formatdate(f)])
        else:
            # This can happen when the expires tag is invalid.
            # reddit.com sends a an expires tag like this: "Thu, 31 Dec
            # 2037 23:59:59 GMT", which is valid RFC 1123, but not
            # strictly correct according to the cookie spec. Browsers
            # appear to parse this tolerantly - maybe we should too.
            # For now, we just ignore this.
            attrs = attrs.with_delitem("expires")

    ret = format_set_cookie_header(name, value, attrs)
    if not ret:
        raise ValueError("Invalid Cookie")
    return ret


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
