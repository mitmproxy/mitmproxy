import warnings
from io import BytesIO
import tempfile
import os
import time
import shutil
from contextlib import contextmanager

from mitmproxy.utils import data
from mitmproxy.net import tcp
from mitmproxy.net import http


test_data = data.Data(__name__).push("../../test/")


@contextmanager
def tmpdir(*args, **kwargs):
    warnings.warn(
        "tutils.tmpdir is deprecated, use pytest's tmpdir fixture instead",
        DeprecationWarning
    )

    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    os.chdir(temp_workdir)

    yield temp_workdir

    os.chdir(orig_workdir)
    shutil.rmtree(temp_workdir)


def treader(bytes):
    """
        Construct a tcp.Read object from bytes.
    """
    fp = BytesIO(bytes)
    return tcp.Reader(fp)


def treq(**kwargs):
    """
    Returns:
        mitmproxy.net.http.Request
    """
    default = dict(
        first_line_format="relative",
        method=b"GET",
        scheme=b"http",
        host=b"address",
        port=22,
        path=b"/path",
        http_version=b"HTTP/1.1",
        headers=http.Headers(((b"header", b"qvalue"), (b"content-length", b"7"))),
        content=b"content"
    )
    default.update(kwargs)
    return http.Request(**default)


def tresp(**kwargs):
    """
    Returns:
        mitmproxy.net.http.Response
    """
    default = dict(
        http_version=b"HTTP/1.1",
        status_code=200,
        reason=b"OK",
        headers=http.Headers(((b"header-response", b"svalue"), (b"content-length", b"7"))),
        content=b"message",
        timestamp_start=time.time(),
        timestamp_end=time.time(),
    )
    default.update(kwargs)
    return http.Response(**default)
