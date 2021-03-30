import asyncio
import json as _json
import logging
import os
import sys
from unittest import mock

import pytest

if sys.platform == 'win32':
    # workaround for
    # https://github.com/tornadoweb/tornado/issues/2751
    # https://www.tornadoweb.org/en/stable/index.html#installation
    # (copied multiple times in the codebase, please remove all occurrences)
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import tornado.testing  # noqa
from tornado import httpclient  # noqa
from tornado import websocket  # noqa

from mitmproxy import options  # noqa
from mitmproxy.test import tflow  # noqa
from mitmproxy.tools.web import app  # noqa
from mitmproxy.tools.web import master as webmaster  # noqa


@pytest.fixture(scope="module")
def no_tornado_logging():
    logging.getLogger('tornado.access').disabled = True
    logging.getLogger('tornado.application').disabled = True
    logging.getLogger('tornado.general').disabled = True
    yield
    logging.getLogger('tornado.access').disabled = False
    logging.getLogger('tornado.application').disabled = False
    logging.getLogger('tornado.general').disabled = False


def json(resp: httpclient.HTTPResponse):
    return _json.loads(resp.body.decode())


@pytest.mark.usefixtures("no_tornado_logging")
class TestApp(tornado.testing.AsyncHTTPTestCase):
    def get_new_ioloop(self):
        io_loop = tornado.platform.asyncio.AsyncIOLoop()
        asyncio.set_event_loop(io_loop.asyncio_loop)
        return io_loop

    def get_app(self):
        o = options.Options(http2=False)
        m = webmaster.WebMaster(o, with_termlog=False)
        f = tflow.tflow(resp=True)
        f.id = "42"
        m.view.add([f])
        m.view.add([tflow.tflow(err=True)])
        m.log.info("test log")
        self.master = m
        self.view = m.view
        self.events = m.events
        webapp = app.Application(m, None)
        webapp.settings["xsrf_cookies"] = False
        return webapp

    def fetch(self, *args, **kwargs) -> httpclient.HTTPResponse:
        # tornado disallows POST without content by default.
        return super().fetch(*args, **kwargs, allow_nonstandard_methods=True)

    def put_json(self, url, data: dict) -> httpclient.HTTPResponse:
        return self.fetch(
            url,
            method="PUT",
            body=_json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

    def test_index(self):
        assert self.fetch("/").code == 200

    def test_filter_help(self):
        assert self.fetch("/filter-help").code == 200

    def test_flows(self):
        resp = self.fetch("/flows")
        assert resp.code == 200
        assert json(resp)[0]["request"]["contentHash"]
        assert json(resp)[1]["error"]

    def test_flows_dump(self):
        resp = self.fetch("/flows/dump")
        assert b"address" in resp.body

    def test_clear(self):
        events = self.events.data.copy()
        flows = list(self.view)

        assert self.fetch("/clear", method="POST").code == 200

        assert not len(self.view)
        assert not len(self.events.data)

        # restore
        for f in flows:
            self.view.add([f])
        self.events.data = events

    def test_resume(self):
        for f in self.view:
            f.intercept()

        assert self.fetch(
            "/flows/42/resume", method="POST").code == 200
        assert sum(f.intercepted for f in self.view) == 1
        assert self.fetch("/flows/resume", method="POST").code == 200
        assert all(not f.intercepted for f in self.view)

    def test_kill(self):
        for f in self.view:
            f.backup()
            f.intercept()

        assert self.fetch("/flows/42/kill", method="POST").code == 200
        assert sum(f.killable for f in self.view) == 1
        assert self.fetch("/flows/kill", method="POST").code == 200
        assert all(not f.killable for f in self.view)
        for f in self.view:
            f.revert()

    def test_flow_delete(self):
        f = self.view.get_by_id("42")
        assert f

        assert self.fetch("/flows/42", method="DELETE").code == 200

        assert not self.view.get_by_id("42")
        self.view.add([f])

        assert self.fetch("/flows/1234", method="DELETE").code == 404

    def test_flow_update(self):
        f = self.view.get_by_id("42")
        assert f.request.method == "GET"
        f.backup()

        upd = {
            "request": {
                "method": "PATCH",
                "port": 123,
                "headers": [("foo", "bar")],
                "content": "req",
            },
            "response": {
                "msg": "Non-Authorisé",
                "code": 404,
                "headers": [("bar", "baz")],
                "content": "resp",
            }
        }
        assert self.put_json("/flows/42", upd).code == 200
        assert f.request.method == "PATCH"
        assert f.request.port == 123
        assert f.request.headers["foo"] == "bar"
        assert f.request.text == "req"
        assert f.response.msg == "Non-Authorisé"
        assert f.response.status_code == 404
        assert f.response.headers["bar"] == "baz"
        assert f.response.text == "resp"

        f.revert()

        assert self.put_json("/flows/42", {"foo": 42}).code == 400
        assert self.put_json("/flows/42", {"request": {"foo": 42}}).code == 400
        assert self.put_json("/flows/42", {"response": {"foo": 42}}).code == 400
        assert self.fetch("/flows/42", method="PUT", body="{}").code == 400
        assert self.fetch(
            "/flows/42",
            method="PUT",
            headers={"Content-Type": "application/json"},
            body="!!"
        ).code == 400

    def test_flow_duplicate(self):
        resp = self.fetch("/flows/42/duplicate", method="POST")
        assert resp.code == 200
        f = self.view.get_by_id(resp.body.decode())
        assert f
        assert f.id != "42"
        self.view.remove([f])

    def test_flow_revert(self):
        f = self.view.get_by_id("42")
        f.backup()
        f.request.method = "PATCH"
        self.fetch("/flows/42/revert", method="POST")
        assert not f._backup

    def test_flow_replay(self):
        with mock.patch("mitmproxy.command.CommandManager.call") as replay_call:
            assert self.fetch("/flows/42/replay", method="POST").code == 200
            assert replay_call.called

    def test_flow_content(self):
        f = self.view.get_by_id("42")
        f.backup()
        f.response.headers["Content-Encoding"] = "ran\x00dom"
        f.response.headers["Content-Disposition"] = 'inline; filename="filename.jpg"'

        r = self.fetch("/flows/42/response/content.data")
        assert r.body == b"message"
        assert r.headers["Content-Encoding"] == "random"
        assert r.headers["Content-Disposition"] == 'attachment; filename="filename.jpg"'

        del f.response.headers["Content-Disposition"]
        f.request.path = "/foo/bar.jpg"
        assert self.fetch(
            "/flows/42/response/content.data"
        ).headers["Content-Disposition"] == 'attachment; filename=bar.jpg'

        f.response.content = b""
        assert self.fetch("/flows/42/response/content.data").code == 400

        f.revert()

    def test_update_flow_content(self):
        assert self.fetch(
            "/flows/42/request/content.data",
            method="POST",
            body="new"
        ).code == 200
        f = self.view.get_by_id("42")
        assert f.request.content == b"new"
        assert f.modified()
        f.revert()

    def test_update_flow_content_multipart(self):
        body = (
            b'--somefancyboundary\r\n'
            b'Content-Disposition: form-data; name="a"; filename="a.txt"\r\n'
            b'\r\n'
            b'such multipart. very wow.\r\n'
            b'--somefancyboundary--\r\n'
        )
        assert self.fetch(
            "/flows/42/request/content.data",
            method="POST",
            headers={"Content-Type": 'multipart/form-data; boundary="somefancyboundary"'},
            body=body
        ).code == 200
        f = self.view.get_by_id("42")
        assert f.request.content == b"such multipart. very wow."
        assert f.modified()
        f.revert()

    def test_flow_content_view(self):
        assert json(self.fetch("/flows/42/request/content/raw")) == {
            "lines": [
                [["text", "content"]]
            ],
            "description": "Raw"
        }

    def test_events(self):
        resp = self.fetch("/events")
        assert resp.code == 200
        assert json(resp)[0]["level"] == "info"

    def test_settings(self):
        assert json(self.fetch("/settings"))["mode"] == "regular"

    def test_settings_update(self):
        assert self.put_json("/settings", {"anticache": True}).code == 200
        assert self.put_json("/settings", {"wtf": True}).code == 400

    def test_options(self):
        j = json(self.fetch("/options"))
        assert type(j) == dict
        assert type(j['anticache']) == dict

    def test_option_update(self):
        assert self.put_json("/options", {"anticache": True}).code == 200
        assert self.put_json("/options", {"wtf": True}).code == 400
        assert self.put_json("/options", {"anticache": "foo"}).code == 400

    def test_option_save(self):
        assert self.fetch("/options/save", method="POST").code == 200

    def test_err(self):
        with mock.patch("mitmproxy.tools.web.app.IndexHandler.get") as f:
            f.side_effect = RuntimeError
            assert self.fetch("/").code == 500

    @tornado.testing.gen_test
    def test_websocket(self):
        ws_url = f"ws://localhost:{self.get_http_port()}/updates"

        ws_client = yield websocket.websocket_connect(ws_url)
        self.master.options.anticomp = True

        r1 = yield ws_client.read_message()
        r2 = yield ws_client.read_message()
        j1 = _json.loads(r1)
        j2 = _json.loads(r2)
        response = dict()
        response[j1['resource']] = j1
        response[j2['resource']] = j2
        assert response['settings'] == {
            "resource": "settings",
            "cmd": "update",
            "data": {"anticomp": True},
        }
        assert response['options'] == {
            "resource": "options",
            "cmd": "update",
            "data": {
                "anticomp": {
                    "value": True,
                    "choices": None,
                    "default": False,
                    "help": "Try to convince servers to send us un-compressed data.",
                    "type": "bool",
                }
            }
        }
        ws_client.close()

        # trigger on_close by opening a second connection.
        ws_client2 = yield websocket.websocket_connect(ws_url)
        ws_client2.close()

    def _test_generate_tflow_js(self):
        _tflow = app.flow_to_json(tflow.tflow(resp=True, err=True))
        # Set some value as constant, so that _tflow.js would not change every time.
        _tflow['client_conn']['id'] = "4a18d1a0-50a1-48dd-9aa6-d45d74282939"
        _tflow['id'] = "d91165be-ca1f-4612-88a9-c0f8696f3e29"
        _tflow['server_conn']['id'] = "f087e7b2-6d0a-41a8-a8f0-e1a4761395f8"
        _tflow["request"]["trailers"] = [["trailer", "qvalue"]]
        _tflow["response"]["trailers"] = [["trailer", "qvalue"]]
        tflow_json = _json.dumps(_tflow, indent=4, sort_keys=True)
        here = os.path.abspath(os.path.dirname(__file__))
        web_root = os.path.join(here, os.pardir, os.pardir, os.pardir, os.pardir, 'web')
        tflow_path = os.path.join(web_root, 'src/js/__tests__/ducks/_tflow.js')
        content = (
            f"/** Auto-generated by test_app.py:TestApp._test_generate_tflow_js */\n"
            f"export default function(){{\n"
            f"    return {tflow_json}\n"
            f"}}"
        )
        with open(tflow_path, 'w', newline="\n") as f:
            f.write(content)
