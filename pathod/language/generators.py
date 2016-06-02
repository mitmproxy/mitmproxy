import string
import random
import mmap

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
    bytes=bytes(bytearray(range(256)))
)


class TransformGenerator(object):

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
        return self.transform(x, d)

    def __getslice__(self, a, b):
        d = self.gen.__getslice__(a, b)
        return self.transform(a, d)

    def __repr__(self):
        return "'transform(%s)'" % self.gen


def rand_byte(chars):
    """
        Return a random character as byte from a charset.
    """
    # bytearray has consistent behaviour on both Python 2 and 3
    # while bytes does not
    return bytes(bytearray([random.choice(chars)]))


class RandomGenerator(object):

    def __init__(self, dtype, length):
        self.dtype = dtype
        self.length = length

    def __len__(self):
        return self.length

    def __getitem__(self, x):
        chars = DATATYPES[self.dtype]
        if isinstance(x, slice):
            return b"".join(rand_byte(chars) for _ in range(*x.indices(self.length)))
        return rand_byte(chars)

    def __repr__(self):
        return "%s random from %s" % (self.length, self.dtype)


class FileGenerator(object):

    def __init__(self, path):
        self.path = path
        self.fp = file(path, "rb")
        self.map = mmap.mmap(self.fp.fileno(), 0, access=mmap.ACCESS_READ)

    def __len__(self):
        return len(self.map)

    def __getitem__(self, x):
        return self.map.__getitem__(x)

    def __getslice__(self, a, b):
        return self.map.__getslice__(a, b)

    def __repr__(self):
        return "<%s" % self.path
