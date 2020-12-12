import asyncio
import json
import sys
from unittest import mock

import flask
import pytest
from flask import request

from .. import tservers
from mitmproxy.addons import asgiapp
from mitmproxy.test import tflow

tapp = flask.Flask(__name__)


@tapp.route("/")
def hello():
    return "testapp"


@tapp.route("/parameters")
def request_check():
    args = {}
    for k in request.args.keys():
        args[k] = request.args[k]
    return json.dumps(args)


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

    def test_parameters(self):
        p = self.pathoc()
        with p.connect():
            ret = p.request("get:'http://testapp/parameters?param1=1&param2=2'")
        assert b'{"param1": "1", "param2": "2"}' == ret.data.content

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

    @pytest.mark.skipif(sys.version_info < (3, 8), reason='requires Python 3.8 or higher')
    def test_app_not_serve_loading_flows(self):
        with mock.patch('mitmproxy.addons.asgiapp.serve') as mck:
            flow = tflow.tflow()
            flow.request.host = "testapp"
            flow.request.port = 80
            asyncio.run_coroutine_threadsafe(self.master.load_flow(flow), self.master.channel.loop).result()
            mck.assert_not_awaited()
