"""
This file must be kept in a python2.7 and python3.5 compatible syntax!
DO NOT use type annotations or other python3.6-only features that makes this file unparsable by older interpreters!
"""

from __future__ import print_function  # this is here for the version check to work on Python 2.

import sys

if sys.version_info < (3, 6):
    # This must be before any mitmproxy imports, as they already break!
    # Keep all other imports below with the 'noqa' magic comment.
    print("#" * 76, file=sys.stderr)
    print("# mitmproxy requires Python 3.6 or higher!                                 #", file=sys.stderr)
    print("#" + " " * 74 + "#", file=sys.stderr)
    print("# Please upgrade your Python intepreter or use our mitmproxy binaries from #", file=sys.stderr)
    print("# https://mitmproxy.org. If your operating system does not include the     #", file=sys.stderr)
    print("# required Python version, you can try using pyenv or similar tools.       #", file=sys.stderr)
    print("#" * 76, file=sys.stderr)
    sys.exit(1)
else:
    from ._main import *  # noqa
