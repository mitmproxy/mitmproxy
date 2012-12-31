import subprocess
import pf

"""
    Doing this the "right" way by using DIOCNATLOOK on the pf device turns out
    to be a pain. Apple has made a number of modifications to the data
    structures returned, and compiling userspace tools to test and work with
    this turns out to be a pain in the ass. Parsing pfctl output is short,
    simple, and works.
"""

class Resolver:
    STATECMD = ("sudo", "-n", "/sbin/pfctl", "-s", "state")
    def __init__(self):
        pass

    def original_addr(self, csock):
        peer = csock.getpeername()
        try:
            stxt = subprocess.check_output(self.STATECMD, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return None
        return pf.lookup(peer[0], peer[1], stxt)
