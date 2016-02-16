import string
import random
import mmap

DATATYPES = dict(
    ascii_letters=string.ascii_letters,
    ascii_lowercase=string.ascii_lowercase,
    ascii_uppercase=string.ascii_uppercase,
    digits=string.digits,
    hexdigits=string.hexdigits,
    octdigits=string.octdigits,
    punctuation=string.punctuation,
    whitespace=string.whitespace,
    ascii=string.printable,
    bytes="".join(chr(i) for i in range(256))
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


class RandomGenerator(object):

    def __init__(self, dtype, length):
        self.dtype = dtype
        self.length = length

    def __len__(self):
        return self.length

    def __getitem__(self, x):
        return random.choice(DATATYPES[self.dtype])

    def __getslice__(self, a, b):
        b = min(b, self.length)
        chars = DATATYPES[self.dtype]
        return "".join(random.choice(chars) for x in range(a, b))

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
