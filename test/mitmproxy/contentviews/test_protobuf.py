from mitmproxy.contentviews import protobuf
from mitmproxy.test import tutils
from . import full_eval

if protobuf.ViewProtobuf.is_available():
    def test_view_protobuf_request():
        v = full_eval(protobuf.ViewProtobuf())

        p = tutils.test_data.path("mitmproxy/data/protobuf01")
        content_type, output = v(open(p, "rb").read())
        assert content_type == "Protobuf"
        assert output.next()[0][1] == '1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"'
