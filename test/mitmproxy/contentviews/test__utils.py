from mitmproxy import tcp
from mitmproxy.contentviews._utils import byte_pairs_to_str_pairs
from mitmproxy.contentviews._utils import get_data
from mitmproxy.contentviews._utils import make_metadata
from mitmproxy.contentviews._utils import merge_repeated_keys
from mitmproxy.contentviews._utils import yaml_dumps
from mitmproxy.contentviews._utils import yaml_loads
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestMetadata:
    def test_make_metadata_http(self):
        with taddons.context():
            f = tflow.tflow()
            metadata = make_metadata(f.request, f)
            assert metadata.http_message == f.request
            assert metadata.flow == f
            assert metadata.content_type is None

            f = tflow.tflow(resp=True)
            f.response.headers["content-type"] = "application/json"
            metadata = make_metadata(f.response, f)
            assert metadata.http_message == f.response
            assert metadata.flow == f
            assert metadata.content_type == "application/json"

    def test_make_metadata_tcp(self):
        with taddons.context():
            f = tflow.ttcpflow()
            msg = f.messages[0]
            metadata = make_metadata(msg, f)
            assert metadata.tcp_message == msg
            assert metadata.flow == f

    def test_make_metadata_udp(self):
        with taddons.context():
            f = tflow.tudpflow()
            msg = f.messages[0]
            metadata = make_metadata(msg, f)
            assert metadata.udp_message == msg
            assert metadata.flow == f

    def test_make_metadata_websocket(self):
        with taddons.context():
            f = tflow.twebsocketflow()
            msg = f.websocket.messages[0]
            metadata = make_metadata(msg, f)
            assert metadata.websocket_message == msg
            assert metadata.flow == f

    def test_make_metadata_dns(self):
        with taddons.context():
            f = tflow.tdnsflow()
            msg = f.request
            metadata = make_metadata(msg, f)
            assert metadata.dns_message == msg
            assert metadata.flow == f


class TestGetData:
    def test_get_data_regular_content(self):
        msg = tcp.TCPMessage(True, b"hello")
        content, enc = get_data(msg)
        assert content == b"hello"
        assert enc == ""

    def test_get_data_http(self):
        f = tflow.tflow()
        f.request.headers["content-encoding"] = "gzip"
        f.request.content = b"content"
        assert f.request.raw_content != f.request.content
        content, enc = get_data(f.request)
        assert content == b"content"
        assert enc == "[decoded gzip]"

    def test_get_data_http_decode_error(self):
        f = tflow.tflow()
        f.request.headers["content-encoding"] = "gzip"
        f.request.raw_content = b"invalid"
        content, enc = get_data(f.request)
        assert content == b"invalid"
        assert enc == "[cannot decode]"


def test_yaml_dumps():
    assert yaml_dumps({}) == ""
    assert yaml_dumps({"foo": "bar"}) == "foo: bar\n"


def test_yaml_loads():
    assert yaml_loads("") is None
    assert yaml_loads("foo: bar\n") == {"foo": "bar"}


def test_merge_repeated_keys():
    assert merge_repeated_keys([]) == {}
    assert merge_repeated_keys([("foo", "bar")]) == {"foo": "bar"}
    assert merge_repeated_keys([("foo", "bar"), ("foo", "baz")]) == {
        "foo": ["bar", "baz"]
    }
    assert merge_repeated_keys(
        [
            ("foo", "bar"),
            ("foo", "baz"),
            ("foo", "qux"),
            ("bar", "quux"),
        ]
    ) == {"foo": ["bar", "baz", "qux"], "bar": "quux"}


def test_byte_pairs_to_str_pairs():
    assert list(byte_pairs_to_str_pairs([(b"foo", b"bar")])) == [("foo", "bar")]
    assert list(byte_pairs_to_str_pairs([(b"\xfa", b"\xff")])) == [(r"\xfa", r"\xff")]
