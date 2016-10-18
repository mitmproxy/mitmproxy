import flask

from .. import tservers
from mitmproxy.builtins import wsgiapp

testapp = flask.Flask(__name__)


@testapp.route("/")
def hello():
    return "testapp"


@testapp.route("/error")
def error():
    raise ValueError("An exception...")


def errapp(environ, start_response):
    raise ValueError("errapp")


class TestApp(tservers.HTTPProxyTest):
    def addons(self):
        return [
            wsgiapp.WSGIApp(testapp, "testapp", 80),
            wsgiapp.WSGIApp(errapp, "errapp", 80)
        ]

    def test_simple(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://testapp/'")
        assert ret.status_code == 200

    def _test_app_err(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://errapp/'")
        assert ret.status_code == 500
        assert b"ValueError" in ret.content


def _test_app_registry():
    ar = flow.AppRegistry()
    ar.add("foo", "domain", 80)

    r = HTTPRequest.wrap(netlib.tutils.treq())
    r.host = "domain"
    r.port = 80
    assert ar.get(r)

    r.port = 81
    assert not ar.get(r)

    r = HTTPRequest.wrap(netlib.tutils.treq())
    r.host = "domain2"
    r.port = 80
    assert not ar.get(r)
    r.headers["host"] = "domain"
    assert ar.get(r)
