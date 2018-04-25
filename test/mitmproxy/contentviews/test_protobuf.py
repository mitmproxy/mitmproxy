import pytest

from mitmproxy.contentviews import protobuf
from mitmproxy.test import tutils
from . import full_eval

data = tutils.test_data.push("mitmproxy/contentviews/test_protobuf_data/")


def test_view_protobuf_request():
    v = full_eval(protobuf.ViewProtobuf())
    p = data.path("protobuf01")

    with open(p, "rb") as f:
        raw = f.read()
    content_type, output = v(raw)
    assert content_type == "Protobuf"
    assert output == [[('text', '1: 3bbc333c-e61c-433b-819a-0b9a8cc103b8')]]
    with pytest.raises(ValueError, match="Failed to parse input."):
        v(b'foobar')


@pytest.mark.parametrize("filename", ["protobuf02", "protobuf03"])
def test_format_pbuf(filename):
    path = data.path(filename)
    with open(path, "rb") as f:
        input = f.read()
    with open(path + "-decoded") as f:
        expected = f.read()

    assert protobuf.format_pbuf(input) == expected
