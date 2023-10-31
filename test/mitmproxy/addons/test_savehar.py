import json
import zlib
from pathlib import Path

import pytest

from mitmproxy import io
from mitmproxy import types
from mitmproxy import version
from mitmproxy.addons.save import Save
from mitmproxy.addons.savehar import SaveHar
from mitmproxy.connection import Server
from mitmproxy.exceptions import OptionsError
from mitmproxy.http import Headers
from mitmproxy.http import Request
from mitmproxy.http import Response
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils

test_dir = Path(__file__).parent.parent


def test_write_error():
    s = SaveHar()

    with pytest.raises(FileNotFoundError):
        s.export_har([], types.Path("unknown_dir/testing_flow.har"))


@pytest.mark.parametrize(
    "header, expected",
    [
        (Headers([(b"cookie", b"foo=bar")]), [{"name": "foo", "value": "bar"}]),
        (
            Headers([(b"cookie", b"foo=bar"), (b"cookie", b"foo=baz")]),
            [{"name": "foo", "value": "bar"}, {"name": "foo", "value": "baz"}],
        ),
    ],
)
def test_request_cookies(header: Headers, expected: list[dict]):
    s = SaveHar()
    req = Request.make("GET", "https://exampls.com", "", header)
    assert s.format_multidict(req.cookies) == expected


@pytest.mark.parametrize(
    "header, expected",
    [
        (
            Headers(
                [
                    (
                        b"set-cookie",
                        b"foo=bar; path=/; domain=.googls.com; priority=high",
                    )
                ]
            ),
            [
                {
                    "name": "foo",
                    "value": "bar",
                    "path": "/",
                    "domain": ".googls.com",
                    "httpOnly": False,
                    "secure": False,
                }
            ],
        ),
        (
            Headers(
                [
                    (
                        b"set-cookie",
                        b"foo=bar; path=/; domain=.googls.com; Secure; HttpOnly; priority=high",
                    ),
                    (
                        b"set-cookie",
                        b"fooz=baz; path=/; domain=.googls.com; priority=high; SameSite=none",
                    ),
                ]
            ),
            [
                {
                    "name": "foo",
                    "value": "bar",
                    "path": "/",
                    "domain": ".googls.com",
                    "httpOnly": True,
                    "secure": True,
                },
                {
                    "name": "fooz",
                    "value": "baz",
                    "path": "/",
                    "domain": ".googls.com",
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "none",
                },
            ],
        ),
    ],
)
def test_response_cookies(header: Headers, expected: list[dict]):
    s = SaveHar()
    resp = Response.make(200, "", header)
    assert s.format_response_cookies(resp) == expected


def test_seen_server_conn():
    s = SaveHar()

    flow = tflow.twebsocketflow()

    servers_seen: set[Server] = set()
    servers_seen.add(flow.server_conn)

    calculated_timings = s.flow_entry(flow, servers_seen)["timings"]

    assert calculated_timings["connect"] == -1.0
    assert calculated_timings["ssl"] == -1.0


def test_timestamp_end():
    s = SaveHar()
    servers_seen: set[Server] = set()
    flow = tflow.twebsocketflow()

    assert s.flow_entry(flow, set())["timings"]["send"] == 1000

    flow.request.timestamp_end = None
    calculated_timings = s.flow_entry(flow, servers_seen)["timings"]

    assert calculated_timings["send"] == 0


def test_tls_setup():
    s = SaveHar()
    servers_seen: set[Server] = set()
    flow = tflow.twebsocketflow()
    flow.server_conn.timestamp_tls_setup = None

    assert s.flow_entry(flow, servers_seen)["timings"]["ssl"] is None


def test_binary_content():
    resp_content = SaveHar().make_har(
        [tflow.tflow(resp=tutils.tresp(content=b"foo" + b"\xFF" * 10))]
    )["log"]["entries"][0]["response"]["content"]
    assert resp_content == {
        "compression": 0,
        "encoding": "base64",
        "mimeType": "",
        "size": 13,
        "text": "Zm9v/////////////w==",
    }


@pytest.mark.parametrize(
    "log_file", [pytest.param(x, id=x.stem) for x in test_dir.glob("data/flows/*.mitm")]
)
def test_savehar(log_file: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(version, "VERSION", "1.2.3")
    s = SaveHar()

    flows = io.read_flows_from_paths([log_file])

    s.export_har(flows, types.Path(tmp_path / "testing_flow.har"))
    expected_har = json.loads(log_file.with_suffix(".har").read_bytes())
    actual_har = json.loads(Path(tmp_path / "testing_flow.har").read_bytes())

    assert actual_har == expected_har


class TestHardumpOption:
    def test_simple(self, capsys):
        s = SaveHar()
        with taddons.context(s) as tctx:
            tctx.configure(s, hardump="-")

            s.response(tflow.tflow())

            s.error(tflow.tflow())

            ws = tflow.twebsocketflow()
            s.response(ws)
            s.websocket_end(ws)

            s.done()

            out = json.loads(capsys.readouterr().out)
            assert len(out["log"]["entries"]) == 3

    def test_filter(self, capsys):
        s = SaveHar()
        with taddons.context(s, Save()) as tctx:
            tctx.configure(s, hardump="-", save_stream_filter="~b foo")
            with pytest.raises(OptionsError):
                tctx.configure(s, save_stream_filter="~~")

            s.response(tflow.tflow(req=tflow.treq(content=b"foo")))
            s.response(tflow.tflow())

            s.done()

            out = json.loads(capsys.readouterr().out)
            assert len(out["log"]["entries"]) == 1

    def test_free(self):
        s = SaveHar()
        with taddons.context(s, Save()) as tctx:
            tctx.configure(s, hardump="-")
            s.response(tflow.tflow())
            assert s.flows
            tctx.configure(s, hardump="")
            assert not s.flows

    def test_compressed(self, tmp_path):
        s = SaveHar()
        with taddons.context(s, Save()) as tctx:
            tctx.configure(s, hardump=str(tmp_path / "out.zhar"))

            s.response(tflow.tflow())
            s.done()

            out = json.loads(zlib.decompress((tmp_path / "out.zhar").read_bytes()))
            assert len(out["log"]["entries"]) == 1


if __name__ == "__main__":
    version.VERSION = "1.2.3"
    s = SaveHar()
    for file in test_dir.glob("data/flows/*.mitm"):
        path = open(file, "rb")
        flows = list(io.FlowReader(path).stream())
        s.export_har(flows, types.Path(test_dir / f"data/flows/{file.stem}.har"))
