import flask

from .. import tservers
from mitmproxy.addons import wsgiapp

tapp = flask.Flask(__name__)


@tapp.route("/")
def hello():
    return "testapp"


@tapp.route("/error")
def error():
    raise ValueError("An exception...")


def errapp(environ, start_response):
    raise ValueError("errapp")


class TestApp(tservers.HTTPProxyTest):
    def addons(self):
        return [
            wsgiapp.WSGIApp(tapp, "testapp", 80),
            wsgiapp.WSGIApp(errapp, "errapp", 80)
        ]

    def test_simple(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://testapp/'")
        assert ret.status_code == 200

    def test_app_err(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://errapp/'")
        assert ret.status_code == 500
        assert b"ValueError" in ret.content
