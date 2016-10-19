import os
import shutil
import tempfile
import argparse
import sys

from contextlib import contextmanager
from unittest.case import SkipTest

import io

import mitmproxy.test.tutils
from mitmproxy import controller
from mitmproxy import connections
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
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
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if err is True:
        err = terr()

    f = DummyFlow(client_conn, server_conn)
    f.error = err
    f.reply = controller.DummyReply()
    return f


def ttcpflow(client_conn=True, server_conn=True, messages=True, err=None):
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if messages is True:
        messages = [
            tcp.TCPMessage(True, b"hello"),
            tcp.TCPMessage(False, b"it's me"),
        ]
    if err is True:
        err = terr()

    f = tcp.TCPFlow(client_conn, server_conn)
    f.messages = messages
    f.error = err
    f.reply = controller.DummyReply()
    return f


def tflow(client_conn=True, server_conn=True, req=True, resp=None, err=None):
    """
    @type client_conn: bool | None | mitmproxy.proxy.connection.ClientConnection
    @type server_conn: bool | None | mitmproxy.proxy.connection.ServerConnection
    @type req:         bool | None | mitmproxy.proxy.protocol.http.HTTPRequest
    @type resp:        bool | None | mitmproxy.proxy.protocol.http.HTTPResponse
    @type err:         bool | None | mitmproxy.proxy.protocol.primitives.Error
    @return:           mitmproxy.proxy.protocol.http.HTTPFlow
    """
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if req is True:
        req = mitmproxy.test.tutils.treq()
    if resp is True:
        resp = mitmproxy.test.tutils.tresp()
    if err is True:
        err = terr()

    if req:
        req = http.HTTPRequest.wrap(req)
    if resp:
        resp = http.HTTPResponse.wrap(resp)

    f = http.HTTPFlow(client_conn, server_conn)
    f.request = req
    f.response = resp
    f.error = err
    f.reply = controller.DummyReply()
    return f


def tclient_conn():
    """
    @return: mitmproxy.proxy.connection.ClientConnection
    """
    c = connections.ClientConnection.from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        clientcert=None,
        ssl_established=False,
        timestamp_start=1,
        timestamp_ssl_setup=2,
        timestamp_end=3,
    ))
    c.reply = controller.DummyReply()
    return c


def tserver_conn():
    """
    @return: mitmproxy.proxy.connection.ServerConnection
    """
    c = connections.ServerConnection.from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        source_address=dict(address=("address", 22), use_ipv6=True),
        ip_address=None,
        cert=None,
        timestamp_start=1,
        timestamp_tcp_setup=2,
        timestamp_ssl_setup=3,
        timestamp_end=4,
        ssl_established=False,
        sni="address",
        via=None
    ))
    c.reply = controller.DummyReply()
    return c


def terr(content="error"):
    """
    @return: mitmproxy.proxy.protocol.primitives.Error
    """
    err = flow.Error(content)
    return err


def get_body_line(last_displayed_body, line_nb):
    return last_displayed_body.contents()[line_nb + 2]


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


class MockParser(argparse.ArgumentParser):

    """
    argparse.ArgumentParser sys.exits() by default.
    Make it more testable by throwing an exception instead.
    """

    def error(self, message):
        raise Exception(message)


raises = mitmproxy.test.tutils.raises


@contextmanager
def capture_stderr(command, *args, **kwargs):
    out, sys.stderr = sys.stderr, io.StringIO()
    command(*args, **kwargs)
    yield sys.stderr.getvalue()
    sys.stderr = out


test_data = data.Data(__name__)
