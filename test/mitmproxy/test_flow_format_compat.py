from mitmproxy.flow import FlowReader
from mitmproxy.exceptions import FlowReadException
from . import tutils


def test_load():
    with open(tutils.test_data.path("data/dumpfile-011"), "rb") as f:
        flow_reader = FlowReader(f)
        flows = list(flow_reader.stream())
        assert len(flows) == 1
        assert flows[0].request.url == "https://example.com/"


def test_cannot_convert():
    with open(tutils.test_data.path("data/dumpfile-010"), "rb") as f:
        flow_reader = FlowReader(f)
        with tutils.raises(FlowReadException):
            list(flow_reader.stream())
