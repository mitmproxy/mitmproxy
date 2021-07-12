import pytest

from mitmproxy import io
from mitmproxy import exceptions


@pytest.mark.parametrize("dumpfile, url, count", [
    ["dumpfile-011.mitm", "https://example.com/", 1],
    ["dumpfile-018.mitm", "https://www.example.com/", 1],
    ["dumpfile-019.mitm", "https://webrv.rtb-seller.com/", 1],
    ["dumpfile-7-websocket.mitm", "https://echo.websocket.org/", 6],
    ["dumpfile-10.mitm", "https://example.com/", 1]
])
def test_load(tdata, dumpfile, url, count):
    with open(tdata.path("mitmproxy/data/" + dumpfile), "rb") as f:
        flow_reader = io.FlowReader(f)
        flows = list(flow_reader.stream())
        assert len(flows) == count
        assert flows[-1].request.url.startswith(url)


def test_cannot_convert(tdata):
    with open(tdata.path("mitmproxy/data/dumpfile-010.mitm"), "rb") as f:
        flow_reader = io.FlowReader(f)
        with pytest.raises(exceptions.FlowReadException):
            list(flow_reader.stream())
