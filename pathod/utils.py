import os
import sys
import netlib.utils


class MemBool(object):

    """
        Truth-checking with a memory, for use in chained if statements.
    """

    def __init__(self):
        self.v = None

    def __call__(self, v):
        self.v = v
        return bool(v)


data = netlib.utils.Data(__name__)


def daemonize(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):  # pragma: no cover
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
    os.chdir("/")
    os.umask(0)
    os.setsid()
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror))
        sys.exit(1)
    si = open(stdin, 'rb')
    so = open(stdout, 'a+b')
    se = open(stderr, 'a+b', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
