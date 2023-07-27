import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from mitmproxy import io
from mitmproxy import types
from mitmproxy.addons.exporthar import ExportHar
from mitmproxy.connection import Server
from mitmproxy.exceptions import CommandError
from mitmproxy.flow import Flow
from mitmproxy.http import Headers
from mitmproxy.http import Request
from mitmproxy.http import Response
from mitmproxy.test import tflow
from mitmproxy.test.tflow import ttcpflow


here = Path(__file__).parent.parent


def test_write_error():
    e = ExportHar()

    with pytest.raises(FileNotFoundError):
        e.export_har([], types.Path("unknown_dir/testing_flow.har"))


def test_command_error():
    e = ExportHar()
    with pytest.raises(CommandError):
        e.export_har([ttcpflow()], types.Path("unknown_dir/testing_flow.har"))


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
    e = ExportHar()
    req = Request.make("GET", "https://example.com", "", header)
    assert e.format_multidict(req.cookies) == expected


@pytest.mark.parametrize(
    "header, expected",
    [
        (
            Headers(
                [
                    (
                        b"set-cookie",
                        b"foo=bar; path=/; domain=.google.com; priority=high",
                    )
                ]
            ),
            [
                {
                    "name": "foo",
                    "value": "bar",
                    "path": "/",
                    "domain": ".google.com",
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
                        b"foo=bar; path=/; domain=.google.com; Secure; HttpOnly; priority=high",
                    ),
                    (
                        b"set-cookie",
                        b"fooz=baz; path=/; domain=.google.com; priority=high; SameSite=none",
                    ),
                ]
            ),
            [
                {
                    "name": "foo",
                    "value": "bar",
                    "path": "/",
                    "domain": ".google.com",
                    "httpOnly": True,
                    "secure": True,
                },
                {
                    "name": "fooz",
                    "value": "baz",
                    "path": "/",
                    "domain": ".google.com",
                    "httpOnly": False,
                    "secure": False,
                    "sameSite": "none",
                },
            ],
        ),
    ],
)
def test_response_cookies(header: Headers, expected: list[dict]):
    e = ExportHar()
    resp = Response.make(200, "", header)
    assert e.format_response_cookies(resp) == expected


def test_seen_server_conn():
    e = ExportHar()

    flow = tflow.twebsocketflow()

    servers_seen: set[Server] = set()
    servers_seen.add(flow.server_conn)

    calculated_timings = e.flow_entry(flow, servers_seen)["timings"]

    assert calculated_timings["connect"] == -1.0
    assert calculated_timings["ssl"] == -1.0


def test_timestamp_end():
    e = ExportHar()
    servers_seen: set[Server] = set()
    flow = tflow.twebsocketflow()

    assert e.flow_entry(flow, set())["timings"]["send"] == 1000

    flow.request.timestamp_end = None
    calculated_timings = e.flow_entry(flow, servers_seen)["timings"]

    assert calculated_timings["send"] == 0


def test_tls_setup():
    e = ExportHar()
    servers_seen: set[Server] = set()
    flow = tflow.twebsocketflow()
    flow.server_conn.timestamp_tls_setup = None

    assert e.flow_entry(flow, servers_seen)["timings"]["ssl"] is None


def test_binary_content():
    e = ExportHar()

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
    } == e.flow_entry(flow, servers_seen)["response"]["content"]


@pytest.mark.parametrize(
    "log_file", [pytest.param(x, id=x.stem) for x in here.glob("data/flows/*.mitm")]
)
def test_exporthar(log_file: Path, tmp_path: Path):
    e = ExportHar()

    flows = io.read_flows_from_paths([log_file])

    e.export_har(flows, types.Path(tmp_path / "testing_flow.har"))
    expected_har = json.loads(
        Path(here / f"data/flows/{log_file.stem}.har").read_bytes()
    )
    actual_har = json.loads(Path(tmp_path / "testing_flow.har").read_bytes())

    assert actual_har == expected_har


if __name__ == "__main__":
    e = ExportHar()

    for file in here.glob("data/flows/*.mitm"):
        if not file.suffix == ".har":
            path = open(file, "rb")
            flows = list(io.FlowReader(path).stream())
            e.export_har(flows, types.Path(here / f"data/flows/{file.stem}.har"))
