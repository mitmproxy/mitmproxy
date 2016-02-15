#
# General code for JSBeautifier unpackers infrastructure. See README.specs
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#

"""General code for JSBeautifier unpackers infrastructure."""

import pkgutil
import re
from . import evalbased

# NOTE: AT THE MOMENT, IT IS DEACTIVATED FOR YOUR SECURITY: it runs js!
BLACKLIST = ['jsbeautifier.unpackers.evalbased']

class UnpackingError(Exception):
    """Badly packed source or general error. Argument is a
    meaningful description."""

def getunpackers():
    """Scans the unpackers dir, finds unpackers and add them to UNPACKERS list.
    An unpacker will be loaded only if it is a valid python module (name must
    adhere to naming conventions) and it is not blacklisted (i.e. inserted
    into BLACKLIST."""
    path = __path__
    prefix = __name__ + '.'
    unpackers = []
    interface = ['unpack', 'detect', 'PRIORITY']
    for _importer, modname, _ispkg in pkgutil.iter_modules(path, prefix):
        if 'tests' not in modname and modname not in BLACKLIST:
            try:
                module = __import__(modname, fromlist=interface)
            except ImportError:
                raise UnpackingError('Bad unpacker: %s' % modname)
            else:
                unpackers.append(module)

    return sorted(unpackers, key = lambda mod: mod.PRIORITY)

UNPACKERS = getunpackers()

def run(source, evalcode=False):
    """Runs the applicable unpackers and return unpacked source as a string."""
    for unpacker in [mod for mod in UNPACKERS if mod.detect(source)]:
        source = unpacker.unpack(source)
    if evalcode and evalbased.detect(source):
        source = evalbased.unpack(source)
    return source

def filtercomments(source):
    """NOT USED: strips trailing comments and put them at the top."""
    trailing_comments = []
    comment = True

    while comment:
        if re.search(r'^\s*\/\*', source):
            comment = source[0, source.index('*/') + 2]
        elif re.search(r'^\s*\/\/', source):
            comment = re.search(r'^\s*\/\/', source).group(0)
        else:
            comment = None

        if comment:
            source = re.sub(r'^\s+', '', source[len(comment):])
            trailing_comments.append(comment)

    return '\n'.join(trailing_comments) + source
