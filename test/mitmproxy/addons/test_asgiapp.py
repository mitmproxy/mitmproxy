import flask

from .. import tservers
from mitmproxy.addons import asgiapp

tapp = flask.Flask(__name__)


@tapp.route("/")
def hello():
    return "testapp"


@tapp.route("/error")
def error():
    raise ValueError("An exception...")


async def errapp(scope, receive, send):
    raise ValueError("errapp")


async def noresponseapp(scope, receive, send):
    return


class TestApp(tservers.HTTPProxyTest):
    def addons(self):
        return [
            asgiapp.WSGIApp(tapp, "testapp", 80),
            asgiapp.ASGIApp(errapp, "errapp", 80),
            asgiapp.ASGIApp(noresponseapp, "noresponseapp", 80),
        ]

    def test_simple(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://testapp/'")
        assert b"testapp" in ret.content

    def test_app_err(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://errapp/?foo=bar'")
        assert ret.status_code == 500
        assert b"ASGI Error" in ret.content

    def test_app_no_response(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://noresponseapp/'")
        assert ret.status_code == 500
        assert b"ASGI Error" in ret.content