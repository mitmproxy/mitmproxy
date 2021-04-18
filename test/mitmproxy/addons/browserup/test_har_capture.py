import json
import pytest
import tempfile
import os
from mitmproxy.test import tflow
from mitmproxy.test.tflow import twebsocketflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy.net.http import cookies
from mitmproxy.utils import data
from mitmproxy.addons.browserup import har_capture_addon
from mitmproxy import websocket
from wsproto.frame_protocol import Opcode

from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes

class TestHARCapture:

    def flow(self, resp_content=b'message'):
        times = dict(
            timestamp_start=746203200,
            timestamp_end=746203290,
        )

        # Create a dummy flow for testing
        return tflow.tflow(
            req=tutils.treq(method=b'GET', **times),
            resp=tutils.tresp(content=resp_content, **times)
        )


    def test_simple(self, hc, path):
        # is invoked if there are exceptions
        # check script is read without errors
        with taddons.context(hc) as tctx:
            assert tctx.master.logs == []

            hc.response(self.flow())

        with tempfile.TemporaryDirectory() as tmpdirname:
            print('Created temporary directory:', tmpdirname)
            file_path = os.path.join(tmpdirname, 'testbase64.har')
            hc.save_har(file_path)
            with open(file_path) as inp:
                har = json.load(inp)
            assert len(har["log"]["entries"]) == 1

    def test_base64(self, hc):
        hc.har_capture_types = [HarCaptureTypes.RESPONSE_BINARY_CONTENT, HarCaptureTypes.RESPONSE_CONTENT ]

        hc.response(self.flow(resp_content=b"foo" + b"\xFF" * 10))
        with tempfile.TemporaryDirectory() as tmpdirname:
            print('Created temporary directory:', tmpdirname)
            file_path = os.path.join(tmpdirname, 'testbase64.har')
            hc.save_har(file_path)
            with open(file_path) as inp:
                har = json.load(inp)
                print(har)
                assert har["log"]["entries"][0]["response"]["content"]["encoding"] == "base64"

    def test_format_cookies(self, hc):
        CA = cookies.CookieAttrs

        f = hc.format_cookies([("n", "v", CA([("k", "v")]))])[0]
        assert f['name'] == "n"
        assert f['value'] == "v"
        assert not f['httpOnly']
        assert not f['secure']

        f = hc.format_cookies([("n", "v", CA([("httponly", None), ("secure", None)]))])[0]
        assert f['httpOnly']
        assert f['secure']

        f = hc.format_cookies([("n", "v", CA([("expires", "Mon, 24-Aug-2037 00:00:00 GMT")]))])[0]
        assert f['expires']

    def test_binary(self, hc, path):
        f = self.flow()
        f.request.method = "POST"
        f.request.headers["content-type"] = "application/x-www-form-urlencoded"
        f.request.content = b"foo=bar&baz=s%c3%bc%c3%9f"
        f.response.headers["random-junk"] = bytes(range(256))
        f.response.content = bytes(range(256))

        hc.response(f)
        with tempfile.TemporaryDirectory() as tmpdirname:
            file_path = os.path.join(tmpdirname, 'testbase64.har')
            hc.save_har(file_path)
            with open(file_path) as inp:
                har = json.load(inp)
                assert len(har["log"]["entries"]) == 1

    def test_capture_cookies_on(self, hc):
        f=self.flow()
        f.request.headers["cookie"] = "foo=bar"
        hc.har_capture_types = [HarCaptureTypes.REQUEST_COOKIES, HarCaptureTypes.REQUEST_CAPTURE_TYPES.REQUEST_CONTENT  ]
        hc.request(f)
        assert(hc.har['log']['entries'][0]['request']['cookies'][0]['name'] == 'foo')
        assert(hc.har['log']['entries'][0]['request']['cookies'][0]['value'] == 'bar')

    def test_capture_cookies_off(self, hc):
        f=self.flow()
        f.request.headers["cookie"] = "foo=bar"
        hc.har_capture_types = [HarCaptureTypes.REQUEST_CAPTURE_TYPES.REQUEST_CONTENT  ]
        hc.request(f)
        assert(hc.har['log']['entries'][0]['request']['cookies'] == [])

    def test_capture_request_headers_on(self, hc):
        f=self.flow()
        f.request.headers["boo"] = "baz"
        hc.har_capture_types = [HarCaptureTypes.REQUEST_CAPTURE_TYPES.REQUEST_HEADERS ]
        hc.request(f)
        assert(hc.har['log']['entries'][0]['request']['headers'][2]['name'] == 'boo')

    def test_capture_request_headers_off(self, hc):
        f=self.flow()
        f.request.headers["cookie"] = "foo=bar"
        hc.har_capture_types = []
        hc.request(f)
        assert(hc.har['log']['entries'][0]['request']['headers'] == [])

    def test_capture_response_headers_on(self, hc):
        f=self.flow()
        f.response.headers["bee"] = "bazl"
        hc.har_capture_types = [HarCaptureTypes.RESPONSE_HEADERS ]
        hc.response(f)
        assert(hc.har['log']['entries'][0]['response']['headers'][2]['name'] == 'bee')

    def test_capture_response_headers_off(self, hc):
        f=self.flow()
        f.response.headers["bee"] = "bazl"
        hc.har_capture_types = []
        hc.response(f)
        assert(hc.har['log']['entries'][0]['response']['headers'] == [])

    def test_websocket_messages_capture_off(self, hc):
        f = twebsocketflow()
        [HarCaptureTypes.RESPONSE_CONTENT]
        hc.response(f)
        hc.websocket_message(f)

        assert(len(hc.har['log']['entries'][0]['_webSocketMessages']) == 0)

    def test_websocket_error_capture(self, hc):
        f = twebsocketflow(err=True)
        hc.har_capture_types = [HarCaptureTypes.WEBSOCKET_MESSAGES ]
        hc.websocket_error(f)
        assert(len(hc.har['log']['entries'][0]['_webSocketMessages']) == 1)

    def test_websocket_messages_capture_on(self, hc):
        f = twebsocketflow()
        hc.har_capture_types = [HarCaptureTypes.WEBSOCKET_MESSAGES ]

        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203)
        ]
        hc.websocket_message(f)
        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203),
            websocket.WebSocketMessage(Opcode.TEXT, True, b"hello text", 946681204)
        ]
        hc.websocket_message(f)

        assert(hc.har['log']['entries'][0]['_webSocketMessages'])


    def test_capture_response_on(self, hc):
        f=self.flow()
        hc.har_capture_types = [HarCaptureTypes.RESPONSE_CONTENT]
        hc.response(f)
        assert(hc.har['log']['entries'][0]['response']['content']['text'] != "")

    def test_capture_response_off(self, hc):
        f=self.flow()
        hc.har_capture_types = []
        hc.response(f)
        assert(hc.har['log']['entries'][0]['response']['content']['text'] == "")

    # if har is cleared, where do existing flow har_entries point?
    def test_new_har_clears_har(self, hc):
        f=self.flow()
        hc.har_capture_types = []
        hc.response(f)
        hc.new_har('','')
        assert(len(hc.har['log']['entries']) == 0)
        f = tflow.tflow(
            req=tutils.treq(method=b'GET'),
            resp=tutils.tresp()
        )
        hc.request(f)
        assert(len(hc.har['log']['pages']) == 1)

    def test_default_page(self, hc):
        f=self.flow()
        hc.request(f)
        assert(hc.har['log']['pages'][0]['id'] == "Default")
        hc.new_har()
        assert(len(hc.har['log']['pages']) == 0)

    def test_har_entries_timings(self, hc):
        f=self.flow()
        hc.request(f)
        assert(hc.har['log']['pages'][0]['id'] == "Default")
    
# def test_servers_seen_resettable:



# def test_default_page_in_new_state:

# def test_ssl_timing_negative_one_for_recycled_connection

# def test_connect_timing_negative_one_for_recycled_connection

@pytest.fixture()
def hc(path):
    a = har_capture_addon.HarCaptureAddOn()
    with taddons.context(hc) as ctx:
        ctx.configure(a, harcapture=path)
    return a


@pytest.fixture()
def tdata():
    return data.Data(__name__)

@pytest.fixture()
def path(tmpdir):
    d = tempfile.TemporaryDirectory().name
    return os.path.join(d, 'test.har')