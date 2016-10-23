import string
import random
import mmap

import sys

DATATYPES = dict(
    ascii_letters=string.ascii_letters.encode(),
    ascii_lowercase=string.ascii_lowercase.encode(),
    ascii_uppercase=string.ascii_uppercase.encode(),
    digits=string.digits.encode(),
    hexdigits=string.hexdigits.encode(),
    octdigits=string.octdigits.encode(),
    punctuation=string.punctuation.encode(),
    whitespace=string.whitespace.encode(),
    ascii=string.printable.encode(),
    bytes=bytes(range(256))
)


class TransformGenerator:

    """
        Perform a byte-by-byte transform another generator - that is, for each
        input byte, the transformation must produce one output byte.

        gen: A generator to wrap
        transform: A function (offset, data) -> transformed
    """

    def __init__(self, gen, transform):
        self.gen = gen
        self.transform = transform

    def __len__(self):
        return len(self.gen)

    def __getitem__(self, x):
        d = self.gen.__getitem__(x)
        if isinstance(x, slice):
            return self.transform(x.start, d)
        return self.transform(x, d)

    def __repr__(self):
        return "'transform(%s)'" % self.gen


def rand_byte(chars):
    """
        Return a random character as byte from a charset.
    """
    # bytearray has consistent behaviour on both Python 2 and 3
    # while bytes does not
    return bytes([random.choice(chars)])


class RandomGenerator:

    def __init__(self, dtype, length):
        self.dtype = dtype
        self.length = length

    def __len__(self):
        return self.length

    def __getitem__(self, x):
        chars = DATATYPES[self.dtype]
        if isinstance(x, slice):
            return b"".join(rand_byte(chars) for _ in range(*x.indices(min(self.length, sys.maxsize))))
        return rand_byte(chars)

    def __repr__(self):
        return "%s random from %s" % (self.length, self.dtype)


class FileGenerator:

    def __init__(self, path):
        self.path = path
        self.fp = open(path, "rb")
        self.map = mmap.mmap(self.fp.fileno(), 0, access=mmap.ACCESS_READ)

    def __len__(self):
        return len(self.map)

    def __getitem__(self, x):
        if isinstance(x, slice):
            return self.map.__getitem__(x)
        # A slice of length 1 returns a byte object (not an integer)
        return self.map.__getitem__(slice(x, x + 1 or self.map.size()))

    def __repr__(self):
        return "<%s" % self.path
