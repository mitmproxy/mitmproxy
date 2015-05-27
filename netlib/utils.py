from __future__ import (absolute_import, print_function, division)


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


class BiDi:

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
