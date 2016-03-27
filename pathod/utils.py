import os
import sys


SIZE_UNITS = dict(
    b=1024 ** 0,
    k=1024 ** 1,
    m=1024 ** 2,
    g=1024 ** 3,
    t=1024 ** 4,
)


class MemBool(object):

    """
        Truth-checking with a memory, for use in chained if statements.
    """

    def __init__(self):
        self.v = None

    def __call__(self, v):
        self.v = v
        return bool(v)


def parse_size(s):
    try:
        return int(s)
    except ValueError:
        pass
    for i in SIZE_UNITS.keys():
        if s.endswith(i):
            try:
                return int(s[:-1]) * SIZE_UNITS[i]
            except ValueError:
                break
    raise ValueError("Invalid size specification.")


def parse_anchor_spec(s):
    """
        Return a tuple, or None on error.
    """
    if "=" not in s:
        return None
    return tuple(s.split("=", 1))


def xrepr(s):
    return repr(s)[1:-1]


def inner_repr(s):
    """
        Returns the inner portion of a string or unicode repr (i.e. without the
        quotes)
    """
    if isinstance(s, unicode):
        return repr(s)[2:-1]
    else:
        return repr(s)[1:-1]


def escape_unprintables(s):
    """
        Like inner_repr, but preserves line breaks.
    """
    s = s.replace("\r\n", "PATHOD_MARKER_RN")
    s = s.replace("\n", "PATHOD_MARKER_N")
    s = inner_repr(s)
    s = s.replace("PATHOD_MARKER_RN", "\n")
    s = s.replace("PATHOD_MARKER_N", "\n")
    return s


class Data(object):

    def __init__(self, name):
        m = __import__(name)
        dirname, _ = os.path.split(m.__file__)
        self.dirname = os.path.abspath(dirname)

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError("dataPath: %s does not exist." % fullpath)
        return fullpath


data = Data(__name__)


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
