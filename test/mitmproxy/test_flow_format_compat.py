from mitmproxy import io
from mitmproxy import exceptions
from mitmproxy.test import tutils


def test_load():
    with open(tutils.test_data.path("mitmproxy/data/dumpfile-011"), "rb") as f:
        flow_reader = io.FlowReader(f)
        flows = list(flow_reader.stream())
        assert len(flows) == 1
        assert flows[0].request.url == "https://example.com/"


def test_cannot_convert():
    with open(tutils.test_data.path("mitmproxy/data/dumpfile-010"), "rb") as f:
        flow_reader = io.FlowReader(f)
        with tutils.raises(exceptions.FlowReadException):
            list(flow_reader.stream())
