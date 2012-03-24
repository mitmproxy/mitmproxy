#
# Unpacker for Dean Edward's p.a.c.k.e.r, a part of javascript beautifier
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

"""Unpacker for Dean Edward's p.a.c.k.e.r"""

import re
import string
from jsbeautifier.unpackers import UnpackingError

PRIORITY = 1

def detect(source):
    """Detects whether `source` is P.A.C.K.E.R. coded."""
    return source.replace(' ', '').startswith('eval(function(p,a,c,k,e,r')

def unpack(source):
    """Unpacks P.A.C.K.E.R. packed js code."""
    payload, symtab, radix, count = _filterargs(source)

    if count != len(symtab):
        raise UnpackingError('Malformed p.a.c.k.e.r. symtab.')

    try:
        unbase = Unbaser(radix)
    except TypeError:
        raise UnpackingError('Unknown p.a.c.k.e.r. encoding.')

    def lookup(match):
        """Look up symbols in the synthetic symtab."""
        word  = match.group(0)
        return symtab[unbase(word)] or word

    source = re.sub(r'\b\w+\b', lookup, payload)
    return _replacestrings(source)

def _filterargs(source):
    """Juice from a source file the four args needed by decoder."""
    argsregex = (r"}\('(.*)', *(\d+), *(\d+), *'(.*)'\."
                 r"split\('\|'\), *(\d+), *(.*)\)\)")
    args = re.search(argsregex, source, re.DOTALL).groups()

    try:
        return args[0], args[3].split('|'), int(args[1]), int(args[2])
    except ValueError:
        raise UnpackingError('Corrupted p.a.c.k.e.r. data.')

def _replacestrings(source):
    """Strip string lookup table (list) and replace values in source."""
    match = re.search(r'var *(_\w+)\=\["(.*?)"\];', source, re.DOTALL)

    if match:
        varname, strings = match.groups()
        startpoint = len(match.group(0))
        lookup = strings.split('","')
        variable = '%s[%%d]' % varname
        for index, value in enumerate(lookup):
            source = source.replace(variable % index, '"%s"' % value)
        return source[startpoint:]
    return source


class Unbaser(object):
    """Functor for a given base. Will efficiently convert
    strings to natural numbers."""
    ALPHABET  = {
        62 : '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ',
        95 : (' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ'
              '[\]^_`abcdefghijklmnopqrstuvwxyz{|}~')
    }

    def __init__(self, base):
        self.base = base

        # If base can be handled by int() builtin, let it do it for us
        if 2 <= base <= 36:
            self.unbase = lambda string: int(string, base)
        else:
            # Build conversion dictionary cache
            try:
                self.dictionary = dict((cipher, index) for
                    index, cipher in enumerate(self.ALPHABET[base]))
            except KeyError:
                raise TypeError('Unsupported base encoding.')

            self.unbase = self._dictunbaser

    def __call__(self, string):
        return self.unbase(string)

    def _dictunbaser(self, string):
        """Decodes a  value to an integer."""
        ret = 0
        for index, cipher in enumerate(string[::-1]):
            ret += (self.base ** index) * self.dictionary[cipher]
        return ret
