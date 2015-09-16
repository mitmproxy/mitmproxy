"""
Having installed a wrong version of pyOpenSSL or netlib is unfortunately a
very common source of error. Check before every start that both versions
are somewhat okay.
"""
from __future__ import division, absolute_import, print_function
import sys
import inspect
import os.path
import six

import OpenSSL
from . import version

PYOPENSSL_MIN_VERSION = (0, 15)


def check_mitmproxy_version(mitmproxy_version, fp=sys.stderr):
    # We don't introduce backward-incompatible changes in patch versions. Only
    # consider major and minor version.
    if version.IVERSION[:2] != mitmproxy_version[:2]:
        print(
            u"You are using mitmproxy %s with netlib %s. "
            u"Most likely, that won't work - please upgrade!" % (
                mitmproxy_version, version.VERSION
            ),
            file=fp
        )
        sys.exit(1)


def check_pyopenssl_version(min_version=PYOPENSSL_MIN_VERSION, fp=sys.stderr):
    min_version_str = u".".join(six.text_type(x) for x in min_version)
    try:
        v = tuple(int(x) for x in OpenSSL.__version__.split(".")[:2])
    except ValueError:
        print(
            u"Cannot parse pyOpenSSL version: {}"
            u"mitmproxy requires pyOpenSSL {} or greater.".format(
                OpenSSL.__version__, min_version_str
            ),
            file=fp
        )
        return
    if v < min_version:
        print(
            u"You are using an outdated version of pyOpenSSL: "
            u"mitmproxy requires pyOpenSSL {} or greater.".format(min_version_str),
            file=fp
        )
        # Some users apparently have multiple versions of pyOpenSSL installed.
        # Report which one we got.
        pyopenssl_path = os.path.dirname(inspect.getfile(OpenSSL))
        print(
            u"Your pyOpenSSL {} installation is located at {}".format(
                OpenSSL.__version__, pyopenssl_path
            ),
            file=fp
        )
        sys.exit(1)
