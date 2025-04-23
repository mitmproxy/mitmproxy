from mitmproxy import tcp
from mitmproxy.contentviews._utils import get_data
from mitmproxy.contentviews._utils import make_metadata
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
