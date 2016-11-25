import subprocess

from . import pf

"""
    Doing this the "right" way by using DIOCNATLOOK on the pf device turns out
    to be a pain. Apple has made a number of modifications to the data
    structures returned, and compiling userspace tools to test and work with
    this turns out to be a pain in the ass. Parsing pfctl output is short,
    simple, and works.

    Note: Also Tested with FreeBSD 10 pkgng Python 2.7.x.
    Should work almost exactly as on Mac OS X and except with some changes to
    the output processing of pfctl (see pf.py).
"""

STATECMD = ("sudo", "-n", "/sbin/pfctl", "-s", "state")


def original_addr(csock):
    peer = csock.getpeername()
    try:
        stxt = subprocess.check_output(STATECMD, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if "sudo: a password is required" in e.output.decode(errors="replace"):
            insufficient_priv = True
        else:
            raise RuntimeError("Error getting pfctl state: " + repr(e))
    else:
        insufficient_priv = "sudo: a password is required" in stxt.decode(errors="replace")

    if insufficient_priv:
        raise RuntimeError(
            "Insufficient privileges to access pfctl. "
            "See http://docs.mitmproxy.org/en/latest/transparent/osx.html for details.")
    return pf.lookup(peer[0], peer[1], stxt)
