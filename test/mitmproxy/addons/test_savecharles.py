import base64
import json

import pytest

from mitmproxy import types
from mitmproxy.addons import savecharles
from mitmproxy.addons.savecharles import SaveCharles
from mitmproxy.test import tflow
from mitmproxy.test import tutils


def test_make_charles_basic():
    s = SaveCharles()
    out = s.make_charles([tflow.tflow(resp=True)])
    assert isinstance(out, list)
    assert len(out) == 1
    entry = out[0]
    assert entry["method"] == "GET"
    assert entry["status"] == "Complete"
    assert entry["request"]["header"]["headers"]
    assert entry["response"]["status"] == 200
    assert entry["protocolVersion"].startswith("HTTP/")
    # round-trip JSON serializable
    json.dumps(out)


def test_make_charles_skips_non_http(caplog):
    s = SaveCharles()
    out = s.make_charles([tflow.ttcpflow()])
    assert out == []


def test_make_charles_error_flow():
    s = SaveCharles()
    f = tflow.tflow(err=True)
    entry = s.make_charles([f])[0]
    assert entry["status"] == "Failed"
    assert entry["response"] is None
    assert entry["failure"]


def test_make_charles_binary_body():
    f = tflow.tflow(resp=tutils.tresp(content=b"foo" + b"\xff" * 10))
    entry = SaveCharles().make_charles([f])[0]
    body = entry["response"]["body"]
    assert "encoded" in body
    assert base64.b64decode(body["encoded"]) == b"foo" + b"\xff" * 10


def test_make_charles_query_split():
    f = tflow.tflow(resp=True)
    f.request.path = "/path?x=1&y=2"
    entry = SaveCharles().make_charles([f])[0]
    assert entry["path"] == "/path"
    assert entry["query"] == "x=1&y=2"


def test_make_charles_websocket():
    f = tflow.twebsocketflow()
    entry = SaveCharles().make_charles([f])[0]
    assert entry["webSocketMessages"]
    assert entry["webSocketMessages"][0]["type"] in ("Send", "Receive")


def test_export_charles_roundtrip(tmp_path):
    out = tmp_path / "session.chlsj"
    s = SaveCharles()
    s.export_charles([tflow.tflow(resp=True)], types.Path(str(out)))
    data = json.loads(out.read_bytes())
    assert isinstance(data, list)
    assert data[0]["method"] == "GET"


def test_export_charles_write_error():
    with pytest.raises(FileNotFoundError):
        SaveCharles().export_charles(
            [tflow.tflow(resp=True)], types.Path("unknown_dir/session.chlsj")
        )


def test_isofmt_none():
    assert savecharles._isofmt(None) is None


def test_ms_helpers():
    assert savecharles._ms(None) == 0
    assert savecharles._ms(-1) == 0
    assert savecharles._ms(0.5) == 500


def test_split_content_type():
    assert savecharles._split_content_type("") == (None, None)
    assert savecharles._split_content_type("text/html") == ("text/html", None)
    assert savecharles._split_content_type('text/html; charset="utf-8"; foo=bar') == (
        "text/html",
        "utf-8",
    )


def test_body_helpers():
    assert savecharles._body(None) == {}
    f = tflow.tflow(resp=True)
    f.response.content = b""
    assert savecharles._body(f.response) == {}


def test_http_version_string_default():
    assert savecharles._http_version_string("") == "HTTP/1.1"
    assert savecharles._http_version_string("HTTP/2.0") == "HTTP/2.0"
    assert savecharles._http_version_string("2.0") == "HTTP/2.0"


def test_make_charles_active_status():
    """No response and no error => Active."""
    f = tflow.tflow()
    f.request.timestamp_end = None
    entry = SaveCharles().make_charles([f])[0]
    assert entry["status"] == "Active"
    assert entry["response"] is None
    # end falls back to start
    assert entry["times"]["end"] == entry["times"]["start"]


def test_make_charles_no_timestamps_in_server_conn():
    f = tflow.tflow(resp=True)
    f.server_conn.timestamp_start = None
    f.server_conn.timestamp_tcp_setup = None
    f.server_conn.timestamp_tls_setup = None
    entry = SaveCharles().make_charles([f])[0]
    assert entry["timing"]["connectMs"] == 0
    assert entry["timing"]["sslMs"] == 0


def test_make_charles_request_only_no_end_ts():
    f = tflow.tflow()
    f.request.timestamp_end = None
    entry = SaveCharles().make_charles([f])[0]
    assert entry["timing"]["requestMs"] == 0
    assert entry["timing"]["latencyMs"] == 0
    # response timing branch
    assert entry["timing"]["responseMs"] == 0


def test_make_charles_text_decode_failure(monkeypatch):
    """get_text returns None => fall back to encoded body."""
    f = tflow.tflow(resp=True)
    f.response.content = b"plain text"
    monkeypatch.setattr(type(f.response), "get_text", lambda self, strict=True: None)
    body = SaveCharles().make_charles([f])[0]["response"]["body"]
    assert "encoded" in body
    assert base64.b64decode(body["encoded"]) == b"plain text"
