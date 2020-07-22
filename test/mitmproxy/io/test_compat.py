import pytest

from mitmproxy import io
from mitmproxy import exceptions


@pytest.mark.parametrize("dumpfile, url", [
    ["dumpfile-011.bin", "https://example.com/"],
    ["dumpfile-018.bin", "https://www.example.com/"],
    ["dumpfile-019.bin", "https://webrv.rtb-seller.com/"],
])
def test_load(tdata, dumpfile, url):
    with open(tdata.path("mitmproxy/data/" + dumpfile), "rb") as f:
        flow_reader = io.FlowReader(f)
        flows = list(flow_reader.stream())
        assert len(flows) == 1
        assert flows[0].request.url.startswith(url)


def test_cannot_convert(tdata):
    with open(tdata.path("mitmproxy/data/dumpfile-010.bin"), "rb") as f:
        flow_reader = io.FlowReader(f)
        with pytest.raises(exceptions.FlowReadException):
            list(flow_reader.stream())
