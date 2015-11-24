import os
import shutil
import tempfile
import argparse
import sys
from cStringIO import StringIO
from contextlib import contextmanager

from unittest.case import SkipTest

import netlib.tutils
from libmproxy import utils, controller
from libmproxy.models import (
    ClientConnection, ServerConnection, Error, HTTPRequest, HTTPResponse, HTTPFlow
)


def _skip_windows(*args):
    raise SkipTest("Skipped on Windows.")


def skip_windows(fn):
    if os.name == "nt":
        return _skip_windows
    else:
        return fn


def _skip_appveyor(*args):
    raise SkipTest("Skipped on AppVeyor.")


def skip_appveyor(fn):
    if "APPVEYOR" in os.environ:
        return _skip_appveyor
    else:
        return fn


def tflow(client_conn=True, server_conn=True, req=True, resp=None, err=None):
    """
    @type client_conn: bool | None | libmproxy.proxy.connection.ClientConnection
    @type server_conn: bool | None | libmproxy.proxy.connection.ServerConnection
    @type req:         bool | None | libmproxy.protocol.http.HTTPRequest
    @type resp:        bool | None | libmproxy.protocol.http.HTTPResponse
    @type err:         bool | None | libmproxy.protocol.primitives.Error
    @return:           bool | None | libmproxy.protocol.http.HTTPFlow
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
    @return: libmproxy.proxy.connection.ClientConnection
    """
    c = ClientConnection.from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        clientcert=None
    ))
    c.reply = controller.DummyReply()
    return c


def tserver_conn():
    """
    @return: libmproxy.proxy.connection.ServerConnection
    """
    c = ServerConnection.from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        state=[],
        source_address=dict(address=("address", 22), use_ipv6=True),
        cert=None
    ))
    c.reply = controller.DummyReply()
    return c


def terr(content="error"):
    """
    @return: libmproxy.protocol.primitives.Error
    """
    err = Error(content)
    return err


def get_body_line(last_displayed_body, line_nb):
    return last_displayed_body.contents()[line_nb + 2]


@contextmanager
def tmpdir(*args, **kwargs):
    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    os.chdir(temp_workdir)

    yield temp_workdir

    os.chdir(orig_workdir)
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
