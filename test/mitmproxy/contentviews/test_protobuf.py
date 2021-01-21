import pytest

from mitmproxy.contentviews import protobuf
from . import full_eval

datadir = "mitmproxy/contentviews/test_protobuf_data/"


def test_view_protobuf_request(tdata):
    v = full_eval(protobuf.ViewProtobuf())
    p = tdata.path(datadir + "protobuf01.bin")

    with open(p, "rb") as f:
        raw = f.read()
    content_type, output = v(raw)
    assert content_type == "Protobuf"
    assert output == [[('text', '1: 3bbc333c-e61c-433b-819a-0b9a8cc103b8')]]
    with pytest.raises(ValueError, match="Failed to parse input."):
        v(b'foobar')


@pytest.mark.parametrize("filename", ["protobuf02.bin", "protobuf03.bin"])
def test_format_pbuf(filename, tdata):
    path = tdata.path(datadir + filename)
    with open(path, "rb") as f:
        input = f.read()
    with open(path.replace(".bin", "-decoded.bin")) as f:
        expected = f.read()

    assert protobuf.format_pbuf(input) == expected


def test_render_priority():
    v = protobuf.ViewProtobuf()
    assert v.render_priority(b"", content_type="application/x-protobuf")
    assert v.render_priority(b"", content_type="application/x-protobuffer")
    assert not v.render_priority(b"", content_type="text/plain")
