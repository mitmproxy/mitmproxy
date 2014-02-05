import os, shutil, tempfile
from contextlib import contextmanager
from libmproxy import flow, utils, controller, proxy
from libmproxy.protocol import http
if os.name != "nt":
    from libmproxy.console.flowview import FlowView
    from libmproxy.console import ConsoleState
from libmproxy.protocol.primitives import Error
from netlib import certutils
from nose.plugins.skip import SkipTest
from mock import Mock
from time import time

def _SkipWindows():
    raise SkipTest("Skipped on Windows.")
def SkipWindows(fn):
    if os.name == "nt":
        return _SkipWindows
    else:
        return fn


def tclient_conn():
    c = proxy.ClientConnection._from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        clientcert=None
    ))
    c.reply = controller.DummyReply()
    return c


def tserver_conn():
    c = proxy.ServerConnection._from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        source_address=dict(address=("address", 22), use_ipv6=True),
        cert=None
    ))
    c.reply = controller.DummyReply()
    return c


def treq(conn=None, content="content"):
    if not conn:
        conn = tclient_conn()
    server_conn = tserver_conn()
    headers = flow.ODictCaseless()
    headers["header"] = ["qvalue"]

    f = http.HTTPFlow(conn, server_conn)
    f.request = http.HTTPRequest("origin", "GET", None, None, None, "/path", (1, 1), headers, content,
                                 None, None, None)
    f.request.reply = controller.DummyReply()
    return f.request


def tresp(req=None, content="message"):
    if not req:
        req = treq()
    f = req.flow

    headers = flow.ODictCaseless()
    headers["header_response"] = ["svalue"]
    cert = certutils.SSLCert.from_der(file(test_data.path("data/dercert"), "rb").read())
    f.server_conn = proxy.ServerConnection._from_state(dict(
        address=dict(address=("address", 22), use_ipv6=True),
        source_address=None,
        cert=cert.to_pem()))
    f.response = http.HTTPResponse((1, 1), 200, "OK", headers, content, time(), time())
    f.response.reply = controller.DummyReply()
    return f.response


def terr(req=None):
    if not req:
        req = treq()
    f = req.flow
    f.error = Error("error")
    f.error.reply = controller.DummyReply()
    return f.error


def tflow(req=None):
    if not req:
        req = treq()
    return req.flow


def tflow_full():
    f = tflow()
    f.response = tresp(f.request)
    return f


def tflow_err():
    f = tflow()
    f.error = terr(f.request)
    return f

def tflowview(request_contents=None):
    m = Mock()
    cs = ConsoleState()
    if request_contents == None:
        flow = tflow()
    else:
        req = treq(None, request_contents)
        flow = tflow(req)

    fv = FlowView(m, cs, flow)
    return fv

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
        apply(obj, args, kwargs)
    except Exception, v:
        if isinstance(exc, basestring):
            if exc.lower() in str(v).lower():
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s"%(
                        repr(str(exc)), v
                    )
                )
        else:
            if isinstance(v, exc):
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s %s"%(
                        exc.__name__, v.__class__.__name__, str(v)
                    )
                )
    raise AssertionError("No exception raised.")

test_data = utils.Data(__name__)
