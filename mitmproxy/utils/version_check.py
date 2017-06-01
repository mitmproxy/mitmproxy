"""
Having installed a wrong version of pyOpenSSL is unfortunately a very common
source of error. Check before every start that both versions are somewhat okay.
"""
import sys
import inspect
import os.path

import OpenSSL

PYOPENSSL_MIN_VERSION = (16, 0)


def check_pyopenssl_version(min_version=PYOPENSSL_MIN_VERSION, fp=sys.stderr):
    min_version_str = ".".join(str(x) for x in min_version)
    try:
        v = tuple(int(x) for x in OpenSSL.__version__.split(".")[:2])
    except ValueError:
        print(
            "Cannot parse pyOpenSSL version: {}"
            "mitmproxy requires pyOpenSSL {} or greater.".format(
                OpenSSL.__version__, min_version_str
            ),
            file=fp
        )
        return
    if v < min_version:
        print(
            "You are using an outdated version of pyOpenSSL: "
            "mitmproxy requires pyOpenSSL {} or greater.".format(min_version_str),
            file=fp
        )
        # Some users apparently have multiple versions of pyOpenSSL installed.
        # Report which one we got.
        pyopenssl_path = os.path.dirname(inspect.getfile(OpenSSL))
        print(
            "Your pyOpenSSL {} installation is located at {}".format(
                OpenSSL.__version__, pyopenssl_path
            ),
            file=fp
        )
        sys.exit(1)
