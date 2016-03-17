import tempfile
from io import BytesIO
import mock
import os
import time
import shutil
from contextlib import contextmanager
import six
import sys
import struct

if sys.version_info.major == 2:
    import Queue
else:
    import queue as Queue

from . import utils, tcp
from .http import Request, Response, Headers


def treader(bytes):
    """
        Construct a tcp.Read object from bytes.
    """
    fp = BytesIO(bytes)
    return tcp.Reader(fp)


@contextmanager
def tmpdir(*args, **kwargs):
    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    os.chdir(temp_workdir)

    yield temp_workdir

    os.chdir(orig_workdir)
    shutil.rmtree(temp_workdir)


def _check_exception(expected, actual, exc_tb):
    if isinstance(expected, six.string_types):
        if expected.lower() not in str(actual).lower():
            six.reraise(AssertionError, AssertionError(
                "Expected %s, but caught %s" % (
                    repr(expected), repr(actual)
                )
            ), exc_tb)
    else:
        if not isinstance(actual, expected):
            six.reraise(AssertionError, AssertionError(
                "Expected %s, but caught %s %s" % (
                    expected.__name__, actual.__class__.__name__, repr(actual)
                )
            ), exc_tb)


def raises(expected_exception, obj=None, *args, **kwargs):
    """
        Assert that a callable raises a specified exception.

        :exc An exception class or a string. If a class, assert that an
        exception of this type is raised. If a string, assert that the string
        occurs in the string representation of the exception, based on a
        case-insenstivie match.

        :obj A callable object.

        :args Arguments to be passsed to the callable.

        :kwargs Arguments to be passed to the callable.
    """
    if obj is None:
        return RaisesContext(expected_exception)
    else:
        try:
            ret = obj(*args, **kwargs)
        except Exception as actual:
            _check_exception(expected_exception, actual, sys.exc_info()[2])
        else:
            raise AssertionError("No exception raised. Return value: {}".format(ret))


class RaisesContext(object):
    def __init__(self, expected_exception):
        self.expected_exception = expected_exception

    def __enter__(self):
        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_type:
            raise AssertionError("No exception raised.")
        else:
            _check_exception(self.expected_exception, exc_val, exc_tb)
        return True


test_data = utils.Data(__name__)
# FIXME: Temporary workaround during repo merge.
import os
test_data.dirname = os.path.join(test_data.dirname,"..","test","netlib")


def treq(**kwargs):
    """
    Returns:
        netlib.http.Request
    """
    default = dict(
        first_line_format="relative",
        method=b"GET",
        scheme=b"http",
        host=b"address",
        port=22,
        path=b"/path",
        http_version=b"HTTP/1.1",
        headers=Headers(header="qvalue", content_length="7"),
        content=b"content"
    )
    default.update(kwargs)
    return Request(**default)


def tresp(**kwargs):
    """
    Returns:
        netlib.http.Response
    """
    default = dict(
        http_version=b"HTTP/1.1",
        status_code=200,
        reason=b"OK",
        headers=Headers(header_response="svalue", content_length="7"),
        content=b"message",
        timestamp_start=time.time(),
        timestamp_end=time.time(),
    )
    default.update(kwargs)
    return Response(**default)


class MockSocketFile(object):

    def __init__(self):
        self.q = Queue.Queue()
        self.closed = False

    def _try_read(self, rlen):
        rs = b''
        while len(rs) < rlen:
            try:
                rs = rs + self.q.get(timeout = 1)
            except Queue.Empty:
                break
        return rs

    def read(self, rlen):
        rs = b''
        while len(rs) < rlen:
            if self.closed and self.q.empty():
                break
            rs = rs + self._try_read(rlen - len(rs))
        return rs

    def write(self, v):
        for i in range(0, len(v)):
            self.q.put(v[i:i + 1])

    def close(self):
        self.closed = True


class MockSocket(object):
    listenMap = {}

    def __init__(self, *args, **kwargs):
        self.wfile = MockSocketFile()
        self.rfile = None
        self.port = 0
        self.llen = 0
        self.targets = []

    def _get_random_port(self):
        i = 1
        while True:
            if i in MockSocket.listenMap.keys():
                i = i + 1
            else:
                break
        return i

    def listen(self, llen):
        self.llen = llen
        if self.port == 0:
            self.port = self._get_random_port()
        MockSocket.listenMap[self.port] = self

    def getsockname(self):
        return ("127.0.0.1", self.port)

    def bind(self, port):
        self.port = port

    def accept(self):
        while len(self.targets) == 0:
            pass
        rs = self.targets[:self.llen]
        self.targets = self.targets[len(rs):]
        return rs

    def connect(self, distaddr):
        if self.port == 0:
            self.port = self._get_random_port()
        if distaddr[1] not in MockSocket.listenMap.keys() or MockSocket.listenMap[distaddr[1]] is None:
            raise OSError()
        s = MockSocket()
        self.rfile = s.wfile
        s.rfile = self.wfile
        MockSocket.listenMap[distaddr[1]].targets.append(s)

    def close(self):
        self.wfile.close()
        if self.rfile is not None:
            self.rfile.close()

    def makefile(self, method, *args):
        if method == "r" or method == "rb":
            return self.rfile
        else:
            return self.wfile
