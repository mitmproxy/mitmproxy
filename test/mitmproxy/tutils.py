import sys
from contextlib import contextmanager
from unittest.case import SkipTest

import io
import mitmproxy.test.tutils
import os
import shutil
import tempfile
from mitmproxy import controller
from mitmproxy import flow
import mitmproxy.test.tflow
from mitmproxy.utils import data


def _skip_windows(*args):
    raise SkipTest("Skipped on Windows.")


def skip_windows(fn):
    if os.name == "nt":
        return _skip_windows
    else:
        return fn


def skip_not_windows(fn):
    if os.name == "nt":
        return fn
    else:
        return _skip_windows


def _skip_appveyor(*args):
    raise SkipTest("Skipped on AppVeyor.")


def skip_appveyor(fn):
    if "APPVEYOR" in os.environ:
        return _skip_appveyor
    else:
        return fn


class DummyFlow(flow.Flow):
    """A flow that is neither HTTP nor TCP."""

    def __init__(self, client_conn, server_conn, live=None):
        super().__init__("dummy", client_conn, server_conn, live)


def tdummyflow(client_conn=True, server_conn=True, err=None):
    if client_conn is True:
        client_conn = mitmproxy.test.tflow.tclient_conn()
    if server_conn is True:
        server_conn = mitmproxy.test.tflow.tserver_conn()
    if err is True:
        err = mitmproxy.test.tflow.terr()

    f = DummyFlow(client_conn, server_conn)
    f.error = err
    f.reply = controller.DummyReply()
    return f


@contextmanager
def chdir(dir):
    orig_dir = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(orig_dir)


@contextmanager
def tmpdir(*args, **kwargs):
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    with chdir(temp_workdir):
        yield temp_workdir
    shutil.rmtree(temp_workdir)


raises = mitmproxy.test.tutils.raises


@contextmanager
def capture_stderr(command, *args, **kwargs):
    out, sys.stderr = sys.stderr, io.StringIO()
    command(*args, **kwargs)
    yield sys.stderr.getvalue()
    sys.stderr = out


test_data = data.Data(__name__)
