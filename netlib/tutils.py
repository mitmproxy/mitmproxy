from io import BytesIO
import tempfile
import os
import time
import shutil
from contextlib import contextmanager
import six
import sys

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
