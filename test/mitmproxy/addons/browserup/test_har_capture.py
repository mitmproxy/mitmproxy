import json
import os
import tempfile

import pytest
from wsproto.frame_protocol import Opcode

from mitmproxy import http
from mitmproxy import websocket
from mitmproxy.addons.browserup import har_capture_addon
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes
from mitmproxy.net.http import cookies
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test.tflow import twebsocketflow
from mitmproxy.utils import data


class TestHARCapture:
    def flow(self, resp_content=b"message"):
        times = dict(
            timestamp_start=746203200,
            timestamp_end=746203290,
        )

        # Create a dummy flow for testing
        return tflow.tflow(
            req=tutils.treq(method=b"GET", **times),
            resp=tutils.tresp(content=resp_content, **times),
        )

    def tvideoflow(self):
        # Create a request object
        req = http.Request.make(
            "GET",
            "http://example.com/video.mp4",
            headers={"Host": "example.com", "User-Agent": "TestAgent"},
        )

        # Create a response object
        resp = http.Response.make(
            200,  # status code
            b"video binary data here",  # video content (truncated for example)
            {
                "Content-Type": "video/mp4",
                "Content-Length": "1234567",  # replace with actual content length
            },
        )
        flow = tflow.tflow(req=req, resp=resp)
        return flow

    def test_capture_dynamic_response_content(self, hc):
        # Test dynamic content (HTML)
        f_dynamic = self.flow()
        f_dynamic.response.headers["Content-Type"] = "text/html"
        f_dynamic.response.content = b"<html><body>Hello World</body></html>"
        hc.har_capture_types = [HarCaptureTypes.RESPONSE_DYNAMIC_CONTENT]
        hc.response(f_dynamic)
        assert (
            hc.har["log"]["entries"][0]["response"]["content"]["text"]
            == "<html><body>Hello World</body></html>"
        )

        # Clear entries for the next test
        hc.har["log"]["entries"].clear()

        # Test non-dynamic content (Video)
        f_video = self.tvideoflow()
        hc.response(f_video)
        assert hc.har["log"]["entries"][0]["response"]["content"]["text"] == ""

    def test_simple(self, hc, path):
        # is invoked if there are exceptions
        # check script is read without errors
        with taddons.context(hc):
            hc.response(self.flow())

        with tempfile.TemporaryDirectory() as tmpdirname:
            print("Created temporary directory:", tmpdirname)
            file_path = os.path.join(tmpdirname, "testbase64.har")
            hc.save_current_har_to_path(file_path)
            with open(file_path) as inp:
                har = json.load(inp)
            assert len(har["log"]["entries"]) == 1

    def test_base64(self, hc):
        hc.har_capture_types = [
            HarCaptureTypes.RESPONSE_BINARY_CONTENT,
            HarCaptureTypes.RESPONSE_CONTENT,
        ]

        hc.response(self.flow(resp_content=b"foo" + b"\xff" * 10))
        with tempfile.TemporaryDirectory() as tmpdirname:
            print("Created temporary directory:", tmpdirname)
            file_path = os.path.join(tmpdirname, "testbase64.har")
            hc.save_current_har_to_path(file_path)
            with open(file_path) as inp:
                har = json.load(inp)
                assert (
                    har["log"]["entries"][0]["response"]["content"]["encoding"]
                    == "base64"
                )

    def test_format_cookies(self, hc):
        CA = cookies.CookieAttrs

        f = hc.format_cookies([("n", "v", CA([("k", "v")]))])[0]
        assert f["name"] == "n"
        assert f["value"] == "v"
        assert not f["httpOnly"]
        assert not f["secure"]

        f = hc.format_cookies([("n", "v", CA([("httponly", None), ("secure", None)]))])[
            0
        ]
        assert f["httpOnly"]
        assert f["secure"]

        f = hc.format_cookies(
            [("n", "v", CA([("expires", "Mon, 24-Aug-2037 00:00:00 GMT")]))]
        )[0]
        assert f["expires"]

    def test_binary(self, hc, path):
        f = self.flow()
        f.request.method = "POST"
        f.request.headers["content-type"] = "application/x-www-form-urlencoded"
        f.request.content = b"foo=bar&baz=s%c3%bc%c3%9f"
        f.response.headers["random-junk"] = bytes(range(256))
        f.response.content = bytes(range(256))

        hc.response(f)
        with tempfile.TemporaryDirectory() as tmpdirname:
            file_path = os.path.join(tmpdirname, "testbase64.har")
            hc.save_current_har_to_path(file_path)
            with open(file_path) as inp:
                har = json.load(inp)
                assert len(har["log"]["entries"]) == 1

    def test_capture_cookies_on(self, hc):
        f = self.flow()
        f.request.headers["cookie"] = "foo=bar"
        hc.har_capture_types = [
            HarCaptureTypes.REQUEST_COOKIES,
            HarCaptureTypes.REQUEST_CAPTURE_TYPES.REQUEST_CONTENT,
        ]
        hc.request(f)
        assert hc.har["log"]["entries"][0]["request"]["cookies"][0]["name"] == "foo"
        assert hc.har["log"]["entries"][0]["request"]["cookies"][0]["value"] == "bar"

    def test_capture_cookies_off(self, hc):
        f = self.flow()
        f.request.headers["cookie"] = "foo=bar"
        hc.har_capture_types = [HarCaptureTypes.REQUEST_CAPTURE_TYPES.REQUEST_CONTENT]
        hc.request(f)
        assert hc.har["log"]["entries"][0]["request"]["cookies"] == []

    def test_capture_request_headers_on(self, hc):
        f = self.flow()
        f.request.headers["boo"] = "baz"
        hc.har_capture_types = [HarCaptureTypes.REQUEST_CAPTURE_TYPES.REQUEST_HEADERS]
        hc.request(f)
        assert hc.har["log"]["entries"][0]["request"]["headers"][2]["name"] == "boo"

    def test_capture_request_headers_off(self, hc):
        f = self.flow()
        f.request.headers["cookie"] = "foo=bar"
        hc.har_capture_types = []
        hc.request(f)
        assert hc.har["log"]["entries"][0]["request"]["headers"] == []

    def test_capture_response_headers_on(self, hc):
        f = self.flow()
        f.response.headers["bee"] = "bazl"
        hc.har_capture_types = [HarCaptureTypes.RESPONSE_HEADERS]
        hc.response(f)
        assert hc.har["log"]["entries"][0]["response"]["headers"][2]["name"] == "bee"

    def test_capture_response_headers_off(self, hc):
        f = self.flow()
        f.response.headers["bee"] = "bazl"
        hc.har_capture_types = []
        hc.response(f)
        assert hc.har["log"]["entries"][0]["response"]["headers"] == []

    def test_websocket_messages_capture_off(self, hc):
        f = twebsocketflow()
        hc.har_capture_types = []
        hc.response(f)
        hc.websocket_message(f)

        assert len(hc.har["log"]["entries"][0]["_webSocketMessages"]) == 0

    def test_websocket_messages_capture_on(self, hc):
        f = twebsocketflow()
        hc.har_capture_types = [HarCaptureTypes.WEBSOCKET_MESSAGES]

        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203)
        ]
        hc.websocket_message(f)
        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203),
            websocket.WebSocketMessage(Opcode.TEXT, True, b"hello text", 946681204),
        ]
        hc.websocket_message(f)
        assert hc.har["log"]["entries"][0]["_webSocketMessages"]

    def test_capture_response_on(self, hc):
        f = self.flow()
        hc.har_capture_types = [HarCaptureTypes.RESPONSE_CONTENT]
        hc.response(f)
        assert hc.har["log"]["entries"][0]["response"]["content"]["text"] != ""

    def test_capture_response_off(self, hc):
        f = self.flow()
        hc.har_capture_types = []
        hc.response(f)
        assert hc.har["log"]["entries"][0]["response"]["content"]["text"] == ""

    # if har is cleared, where do existing flow har_entries point?
    def test_new_har_clears_har(self, hc):
        f = self.flow()
        hc.har_capture_types = []
        hc.response(f)
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["entries"]) == 0
        f = tflow.tflow(req=tutils.treq(method=b"GET"), resp=tutils.tresp())
        hc.request(f)
        assert len(hc.har["log"]["pages"]) == 1

    def test_blank_default_page(self, hc):
        f = self.flow()
        hc.request(f)
        assert hc.har["log"]["pages"][0]["id"] == "page_1"
        assert hc.har["log"]["pages"][0]["title"] == "Default"
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["pages"]) == 1

    def test_har_entries_timings(self, hc):
        f = self.flow()
        hc.request(f)
        assert hc.har["log"]["pages"][0]["id"] == "page_1"

    def test_reset_har_removes_pages_and_entries(self, hc):
        f = self.flow()
        hc.request(f)
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["pages"]) == 1
        assert len(hc.har["log"]["entries"]) == 0

    # test reset returns old har
    def test_reset_returns_old_har(self, hc):
        f = self.flow()
        hc.request(f)
        old_har = hc.reset_har_and_return_old_har()
        assert len(old_har["log"]["pages"]) == 1
        assert len(old_har["log"]["entries"]) == 1

    def test_reset_inits_empty_first_page(self, hc):
        f = self.flow()
        hc.request(f)
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["pages"]) == 1
        assert len(hc.har["log"]["entries"]) == 0

    def test_filter_submitted_entries(self, hc):
        f = self.flow()
        hc.request(f)
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["pages"]) == 1
        assert len(hc.har["log"]["entries"]) == 0

    def test_clean_har(self, hc):
        f = self.flow()
        hc.request(f)
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["pages"]) == 1
        assert len(hc.har["log"]["entries"]) == 0

    def test_uncleaned_video_har_entries_still_there(self, hc):
        f = self.tvideoflow()
        hc.request(f)
        hc.response(f)

        h = hc.create_filtered_har_and_track_submitted()
        assert len(h["log"]["entries"]) == 1

        assert hc.har["log"]["entries"][0]["request"]["_submitted"] is True
        assert not hc.har["log"]["entries"][0]["response"].get("_submitted")

        # test filtering
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["pages"]) == 1
        assert len(hc.har["log"]["entries"]) == 0

    def test_uncleaned_websocket_har_entries_still_there(self, hc):
        f = self.flow()
        hc.request(f)

        f = twebsocketflow()
        hc.request(f)
        hc.response(f)

        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203)
        ]
        hc.websocket_message(f)
        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203),
            websocket.WebSocketMessage(Opcode.TEXT, True, b"hello text", 946681204),
        ]
        hc.websocket_message(f)

        hc.create_filtered_har_and_track_submitted()

        assert len(hc.har["log"]["entries"]) == 2
        assert hc.har["log"]["entries"][0]["request"].get("_submitted")

        assert hc.har["log"]["entries"][1]["request"].get("_submitted")
        assert not hc.har["log"]["entries"][1]["response"].get("_submitted")

        # test filtering
        hc.reset_har_and_return_old_har()
        assert len(hc.har["log"]["pages"]) == 1
        assert len(hc.har["log"]["entries"]) == 0

    def test_full_submit(self, hc):
        # combine video and websocket flows and regular flow.
        # Then call create_filtered_har_and_track_submitted(self, report_last_page = True, include_websockets = True, include_videos = True)
        # assert that there are no entries, and no pages
        f = self.flow()
        hc.request(f)
        hc.response(f)
        f = self.tvideoflow()
        hc.request(f)
        hc.response(f)

        f = twebsocketflow()
        hc.request(f)
        f = self.flow()

        filtered_result = hc.create_filtered_har_and_track_submitted(
            report_last_page=True, include_websockets=True, include_videos=True
        )

        assert len(filtered_result["log"]["entries"]) == 3

        # loop through har entries and assert that they are all submitted
        for entry in hc.har["log"]["entries"]:
            assert entry["request"].get("_submitted")
            assert entry["response"].get("_submitted")

        # loop through har pages and assert that they are all submitted
        for page in hc.har["log"]["pages"]:
            assert page.get("_submitted")

        old_har = hc.reset_har_and_return_old_har()
        assert len(old_har["log"]["entries"]) == 3

        assert len(hc.har["log"]["entries"]) == 0

        assert len(hc.har["log"]["pages"]) == 1
        assert hc.har["log"]["pages"][0]["id"] == "page_1"


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
    return os.path.join(d, "test.har")
