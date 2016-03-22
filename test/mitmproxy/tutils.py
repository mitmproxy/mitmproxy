import os
import shutil
import tempfile
import argparse
import sys
from six.moves import cStringIO as StringIO
from contextlib import contextmanager

from unittest.case import SkipTest

import netlib.tutils
from mitmproxy import utils, controller
from mitmproxy.models import (
    ClientConnection, ServerConnection, Error, HTTPRequest, HTTPResponse, HTTPFlow
)


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


def tflow(client_conn=True, server_conn=True, req=True, resp=None, err=None):
    """
    @type client_conn: bool | None | mitmproxy.proxy.connection.ClientConnection
    @type server_conn: bool | None | mitmproxy.proxy.connection.ServerConnection
    @type req:         bool | None | mitmproxy.protocol.http.HTTPRequest
    @type resp:        bool | None | mitmproxy.protocol.http.HTTPResponse
    @type err:         bool | None | mitmproxy.protocol.primitives.Error
    @return:           bool | None | mitmproxy.protocol.http.HTTPFlow
    """
    if client_conn is True:
        client_conn = tclient_conn()
    if server_conn is True:
        server_conn = tserver_conn()
    if req is True:
        req = netlib.tutils.treq()
    if resp is True:
        resp = netlib.tutils.tresp()
    if err is True:
        err = terr()

    if req:
        req = HTTPRequest.wrap(req)
    if resp:
        resp = HTTPResponse.wrap(resp)

    f = HTTPFlow(client_conn, server_conn)
    f.request = req
    f.response = resp
    f.error = err
    f.reply = controller.DummyReply()
    return f


def tclient_conn():
    """
    @return: mitmproxy.proxy.connection.ClientConnection
    """
    c = ClientConnection.from_state(dict(
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
    c = ServerConnection.from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        source_address=dict(address=("address", 22), use_ipv6=True),
        peer_address=None,
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
    @return: mitmproxy.protocol.primitives.Error
    """
    err = Error(content)
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


raises = netlib.tutils.raises


@contextmanager
def capture_stderr(command, *args, **kwargs):
    out, sys.stderr = sys.stderr, StringIO()
    command(*args, **kwargs)
    yield sys.stderr.getvalue()
    sys.stderr = out


test_data = utils.Data(__name__)
