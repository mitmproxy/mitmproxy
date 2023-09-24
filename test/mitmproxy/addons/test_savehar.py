import json
import zlib
from pathlib import Path

import pytest

from mitmproxy import http
from mitmproxy import io
from mitmproxy import types
from mitmproxy import version
from mitmproxy.addons.savehar import SaveHar
from mitmproxy.connection import Server
from mitmproxy.http import Headers
from mitmproxy.http import Request
from mitmproxy.http import Response
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils


test_dir = Path(__file__).parent.parent
mitmproxy_dir = test_dir.parent.parent


def flow(resp_content=b"message"):
    times = dict(
        timestamp_start=746203272,
        timestamp_end=746203272,
    )

    return tflow.tflow(
        req=tutils.treq(method=b"GET", **times),
        resp=tutils.tresp(content=resp_content, **times),
    )


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
    s = SaveHar()

    flow = tflow.twebsocketflow()
    assert flow.response

    flow.response.set_content(b"\xFF")
    servers_seen: set[Server] = set()

    assert flow.response.content

    assert {
        "size": 1,
        "compression": 0,
        "mimeType": "",
        "text": "/w==",
        "encoding": "base64",
    } == s.flow_entry(flow, servers_seen)["response"]["content"]


@pytest.mark.parametrize(
    "log_file", [pytest.param(x, id=x.stem) for x in test_dir.glob("data/flows/*.mitm")]
)
def test_savehar(log_file: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(version, "VERSION", "1.2.3")
    s = SaveHar()

    flows = io.read_flows_from_paths([log_file])

    s.export_har(flows, types.Path(tmp_path / "testing_flow.har"))
    expected_har = json.loads(
        log_file.with_suffix(".har").read_bytes()
    )
    actual_har = json.loads(Path(tmp_path / "testing_flow.har").read_bytes())

    assert actual_har == expected_har


def test_savehar_dump(tmpdir, monkeypatch):
    monkeypatch.setattr(version, "VERSION", "1.2.3")
    with taddons.context() as tctx:
        s = SaveHar()
        assert s
        path = str(tmpdir.join("somefile"))
        tctx.configure(s, hardump=path)

        for x in io.read_flows_from_paths(
            [Path(test_dir / "data/flows/websocket.mitm")]
        ):
            assert isinstance(x, http.HTTPFlow)
            s.websocket_end(x)

        s.done()

        with open(path) as inp:
            har = json.load(inp)
        assert har == json.loads(
            Path(test_dir / f"data/flows/websocket.har").read_bytes()
        )


def test_options(capfd, monkeypatch):
    monkeypatch.setattr(version, "VERSION", "1.2.3")
    with taddons.context() as tctx:
        s = SaveHar()
        assert s
        tctx.configure(s, hardump="-")

        for x in io.read_flows_from_paths(
            [Path(test_dir / "data/flows/websocket.mitm")]
        ):
            assert isinstance(x, http.HTTPFlow)
            s.websocket_end(x)
        s.done()
        out, _ = capfd.readouterr()
        out_har = json.loads(out)
        assert out_har == json.loads(
            Path(test_dir / f"data/flows/websocket.har").read_bytes()
        )


def test_base64(tmpdir):
    with taddons.context() as tctx:
        s = SaveHar()
        assert s
        path = str(tmpdir.join("somefile"))
        tctx.configure(s, hardump=path)

        s.response(
            tflow.tflow(resp=tutils.tresp(content=b"foo" + b"\xFF" * 10))
        )
        s.done()
        with open(path) as inp:
            har = json.load(inp)
        assert har["log"]["entries"][0]["response"]["content"]["encoding"] == "base64"


if __name__ == "__main__":
    version.VERSION = "1.2.3"
    s = SaveHar()
    for file in test_dir.glob("data/flows/*.mitm"):
        path = open(file, "rb")
        flows = list(io.FlowReader(path).stream())
        s.export_har(flows, types.Path(test_dir / f"data/flows/{file.stem}.har"))
