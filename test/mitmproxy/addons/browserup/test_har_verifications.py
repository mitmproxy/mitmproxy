import jsonpath_ng
import pytest
import tempfile
import os
from mitmproxy.test import tflow
from mitmproxy.test.tflow import twebsocketflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy.addons.browserup import har_capture_addon
from mitmproxy import websocket
from wsproto.frame_protocol import Opcode
from mitmproxy.addons.browserup.har.har_verifications import HarVerifications

from mitmproxy.addons.browserup.har.har_capture_types import HarCaptureTypes

class TestHARVerifications:

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

    def test_responses(self, hc, path):
        hv = HarVerifications.new(har)
        hv.response_less_than(1.2)


#def content_contains(self, str):
   # def content_does_not_contain(self, str):
   # def content_matches(self, rxp):
   # def content_size_less_than_or_equal(self, size):

#def headers_contain_string(self, str):
   # def headers_do_not_contain_string(self, str):
   # def headers_match(self, rxp):

#def web_socket_messages_contain(self, str):
   # def web_socket_messages_contain(self, rxp):


#def all_pages_load_in()

#def slowest_(page load, onload, paint, )

#def fastest()

#def 90th()

@pytest.fixture()
def har(self, hc):
    f = self.flow()
    hc.request(f)
    hc.response(f)
    hc.request(f)
    return hc.har

@pytest.fixture()
def hc():
    a = har_capture_addon.HarCaptureAddOn()
    with taddons.context(hc) as ctx:
        ctx.configure(a)
    return a