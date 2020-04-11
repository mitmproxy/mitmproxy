import pytest

from mitmproxy import io
from mitmproxy import exceptions


def test_load(tdata):
    with open(tdata.path("mitmproxy/data/dumpfile-011.bin"), "rb") as f:
        flow_reader = io.FlowReader(f)
        flows = list(flow_reader.stream())
        assert len(flows) == 1
        assert flows[0].request.url == "https://example.com/"


def test_load_018(tdata):
    with open(tdata.path("mitmproxy/data/dumpfile-018.bin"), "rb") as f:
        flow_reader = io.FlowReader(f)
        flows = list(flow_reader.stream())
        assert len(flows) == 1
        assert flows[0].request.url == "https://www.example.com/"


def test_cannot_convert(tdata):
    with open(tdata.path("mitmproxy/data/dumpfile-010.bin"), "rb") as f:
        flow_reader = io.FlowReader(f)
        with pytest.raises(exceptions.FlowReadException):
            list(flow_reader.stream())
