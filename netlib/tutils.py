import cStringIO
import tempfile
import os
import time
import shutil
from contextlib import contextmanager

from netlib import tcp, utils, http


def treader(bytes):
    """
        Construct a tcp.Read object from bytes.
    """
    fp = cStringIO.StringIO(bytes)
    return tcp.Reader(fp)


@contextmanager
def tmpdir(*args, **kwargs):
    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    os.chdir(temp_workdir)

    yield temp_workdir

    os.chdir(orig_workdir)
    shutil.rmtree(temp_workdir)


def raises(exc, obj, *args, **kwargs):
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
    try:
        ret = obj(*args, **kwargs)
    except Exception as v:
        if isinstance(exc, basestring):
            if exc.lower() in str(v).lower():
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s" % (
                        repr(str(exc)), v
                    )
                )
        else:
            if isinstance(v, exc):
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s %s" % (
                        exc.__name__, v.__class__.__name__, str(v)
                    )
                )
    raise AssertionError("No exception raised. Return value: {}".format(ret))

test_data = utils.Data(__name__)


def treq(content="content", scheme="http", host="address", port=22):
    """
    @return: libmproxy.protocol.http.HTTPRequest
    """
    headers = http.Headers()
    headers["header"] = "qvalue"
    req = http.Request(
        "relative",
        "GET",
        scheme,
        host,
        port,
        "/path",
        (1, 1),
        headers,
        content,
        None,
        None,
    )
    return req


def treq_absolute(content="content"):
    """
    @return: libmproxy.protocol.http.HTTPRequest
    """
    r = treq(content)
    r.form_in = r.form_out = "absolute"
    r.host = "address"
    r.port = 22
    r.scheme = "http"
    return r


def tresp(content="message"):
    """
    @return: libmproxy.protocol.http.HTTPResponse
    """

    headers = http.Headers()
    headers["header_response"] = "svalue"

    resp = http.semantics.Response(
        (1, 1),
        200,
        "OK",
        headers,
        content,
        timestamp_start=time.time(),
        timestamp_end=time.time(),
    )
    return resp
