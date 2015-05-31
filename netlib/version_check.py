from __future__ import print_function, absolute_import
import sys
import inspect
import os.path

import OpenSSL
from . import version

PYOPENSSL_MIN_VERSION = (0, 15)


def version_check(
        mitmproxy_version,
        pyopenssl_min_version=PYOPENSSL_MIN_VERSION,
        fp=sys.stderr):
    """
    Having installed a wrong version of pyOpenSSL or netlib is unfortunately a
    very common source of error. Check before every start that both versions
    are somewhat okay.
    """
    # We don't introduce backward-incompatible changes in patch versions. Only
    # consider major and minor version.
    if version.IVERSION[:2] != mitmproxy_version[:2]:
        print(
            "You are using mitmproxy %s with netlib %s. "
            "Most likely, that won't work - please upgrade!" % (
                mitmproxy_version, version.VERSION
            ),
            file=fp
        )
        sys.exit(1)
    v = tuple([int(x) for x in OpenSSL.__version__.split(".")][:2])
    if v < pyopenssl_min_version:
        print(
            "You are using an outdated version of pyOpenSSL:"
            " mitmproxy requires pyOpenSSL %x or greater." %
            pyopenssl_min_version,
            file=fp
        )
        # Some users apparently have multiple versions of pyOpenSSL installed.
        # Report which one we got.
        pyopenssl_path = os.path.dirname(inspect.getfile(OpenSSL))
        print(
            "Your pyOpenSSL %s installation is located at %s" % (
                OpenSSL.__version__, pyopenssl_path
            ),
            file=fp
        )
        sys.exit(1)
