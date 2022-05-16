import pytest
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy import http

from mitmproxy.addons.browserup import har_capture_addon
from mitmproxy.addons.browserup.har.har_verifications import HarVerifications
from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes
from mitmproxy.test.tflow import twebsocketflow
from mitmproxy import websocket
from wsproto.frame_protocol import Opcode


class TestHARVerifications:

    def test_response_missing_fails(self, hc, flow):
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200'}) is False)

    def test_response_present_succeeds(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200'}))

    def test_page_response_present_succeeds(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'page': 'Default'}))

    def test_page_response_missing_page(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'page': 'NoSuch'}) is False)

    def test_page_response_page_current(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'page': 'current'}))

    def test_response_present_url_succeeds(self, hc, flow):
        hc.request(flow)
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'url': r'/path'}))

    def test_response_present_url_false(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'url': r'nope'}) is False)

    def test_response_content_present(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'content': r'message'}))

    def test_response_content_not_present(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'content': r'notThere'}) is False)

    def test_response_present_false(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '300'}) is False)

    def test_response_not_present(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.not_present({'status': '200'}) is False)

    def test_response_present_header_missing(self, hc, flow):
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'response_header': {'name': 'Nothere'}}) is False)

    def test_request_present_cookie(self, hc, flow):
        flow.request.headers["Cookie"] = b'foo=bar'
        hc.request(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'request_cookie': {'name': 'foo'}}))

    def test_response_header_match(self, hc, flow):
        hc.har_capture_types
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'response_header': {'name': r'content-length'}}))

    def test_header_key_val_both_match(self, hc, flow):
        hc.har_capture_types
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'response_header': {'name': r'content-length', 'value': '7'}}))

    def test_request_header_key_val_both_match(self, hc, flow):
        hc.har_capture_types
        hc.request(flow)
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'request_header': {'name': r'content-length', 'value': '7'}}))

    def test_header_key_no_val_match(self, hc, flow):
        hc.har_capture_types
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'response_header': {'name': r'content-length', 'value': '9'}}) is False)

    def test_header_no_match(self, hc, flow):
        hc.har_capture_types
        hc.response(flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'status': '200', 'response_header': {'name': r'nope'}}) is False)

    def test_websocket_messages_match(self, hc):
        f = twebsocketflow()
        hc.har_capture_types = [HarCaptureTypes.WEBSOCKET_MESSAGES]

        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203)
        ]
        hc.websocket_message(f)
        f.websocket.messages = [
            websocket.WebSocketMessage(Opcode.BINARY, True, b"hello binary", 946681203),
            websocket.WebSocketMessage(Opcode.TEXT, True, "hello text", 946681204)
        ]
        hc.websocket_message(f)

        hv = HarVerifications(hc.har)
        assert(hv.present({'websocket_message': 'hello'}))

    def test_websocket_messages_no_match(self, hc):
        hv = HarVerifications(hc.har)
        assert(hv.present({'websocket_message': 'hello'}) is False)

    def test_content_type(self, hc, json_flow):
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'content_type': 'application/json'}))

    def test_json_valid(self, hc, json_flow):
        hc.request(json_flow)
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'json_valid': True}))

    def test_json_path(self, hc, json_flow):
        hc.request(json_flow)
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'json_path': '$.foo'}))

    def test_missing_json_path(self, hc, json_flow):
        hc.request(json_flow)
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        assert(hv.present({'json_path': '$.nope'}) is False)

    def test_json_schema(self, hc, json_flow):
        hc.request(json_flow)
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        schema = {"type": "object", "properties": {"foo": {"type": "string"}}}
        assert(hv.present({'json_schema': schema}))

    def test_json_schema_not_valid(self, hc, json_flow):
        hc.request(json_flow)
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        schema = {"type": "object", "properties": {"foo": {"type": "integer"}}}
        assert(hv.present({'json_schema': schema}) is False)

    def test_time_max(self, hc, json_flow):
        hc.request(json_flow)
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        assert(hv.get_max({'status': '200'}, 'time'))

    def test_size_max(self, hc, json_flow):
        hc.request(json_flow)
        hc.response(json_flow)
        hv = HarVerifications(hc.har)
        assert(hv.get_max({'status': '200'}, 'response'))


@pytest.fixture()
def flow():
    resp_content = b'message'
    times = dict(
        timestamp_start=746203200,
        timestamp_end=746203290,
    )

    return tflow.tflow(
        req=tutils.treq(method=b'GET', **times),
        resp=tutils.tresp(content=resp_content, **times)
    )


@pytest.fixture()
def json_flow():
    times = dict(
        timestamp_start=746203200,
        timestamp_end=746203290,
    )

    return tflow.tflow(
        req=tutils.treq(method=b'GET', path=b"/path/foo.json", **times),
        resp=tutils.tresp(content=b'{"foo": "bar"}',
                          headers=http.Headers(((b"header-response", b"svalue"), (b"content-type", b"application/json"))), **times)
    )


@pytest.fixture()
def hc(flow):
    a = har_capture_addon.HarCaptureAddOn()
    with taddons.context(hc) as ctx:
        ctx.configure(a)
    return a
