"""
A flexible module for cookie parsing and manipulation.

We try to be as permissive as possible. Parsing accepts formats from RFC6265 an
RFC2109. Serialization follows RFC6265 strictly.

    http://tools.ietf.org/html/rfc6265
    http://tools.ietf.org/html/rfc2109
"""

import re

import odict


def _read_until(s, start, term):
    """
        Read until one of the characters in term is reached.
    """
    if start == len(s):
        return "", start+1
    for i in range(start, len(s)):
        if s[i] in term:
            return s[start:i], i
    return s[start:i+1], i+1


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
    for i in range(start+1, len(s)):
        if escaping:
            ret.append(s[i])
            escaping = False
        elif s[i] == '"':
            break
        elif s[i] == "\\":
            escaping = True
            pass
        else:
            ret.append(s[i])
    return "".join(ret), i+1


def _read_value(s, start, special):
    """
        Reads a value - the RHS of a token/value pair in a cookie.

        special: If the value is special, commas are premitted. Else comma
        terminates. This helps us support old and new style values.
    """
    if start >= len(s):
        return "", start
    elif s[start] == '"':
        return _read_quoted_string(s, start)
    elif special:
        return _read_until(s, start, ";")
    else:
        return _read_until(s, start, ";,")


def _read_pairs(s, specials=()):
    """
        Read pairs of lhs=rhs values.

        specials: A lower-cased list of keys that may contain commas.
    """
    off = 0
    vals = []
    while 1:
        lhs, off = _read_token(s, off)
        lhs = lhs.lstrip()
        rhs = None
        if off < len(s):
            if s[off] == "=":
                rhs, off = _read_value(s, off+1, lhs.lower() in specials)
        vals.append([lhs, rhs])
        off += 1
        if not off < len(s):
            break
    return vals, off


ESCAPE = re.compile(r"([\"\\])")


def _has_special(s):
    for i in s:
        if i in '",;\\':
            return True
        o = ord(i)
        if o < 0x21 or o > 0x7e:
            return True
    return False


def _format_pairs(lst, specials=()):
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
                v = '"%s"'%v
            vals.append("%s=%s"%(k, v))
    return "; ".join(vals)


def parse_cookies(s):
    """
        Parses a Cookie header value.
        Returns an ODict object.
    """
    pairs, off = _read_pairs(s)
    return odict.ODict(pairs)


def unparse_cookies(od):
    """
        Formats a Cookie header value.
    """
    return _format_pairs(od.lst)


def parse_set_cookies(s):
    start = 0


def unparse_set_cookies(s):
    pass
