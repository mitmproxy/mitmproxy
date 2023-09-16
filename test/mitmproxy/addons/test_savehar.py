import json
from pathlib import Path

import pytest
import zlib
from mitmproxy import io
from mitmproxy import types
from mitmproxy import version
from mitmproxy.addons.savehar import SaveHar, done, load, response, websocket_end
from mitmproxy.net.http import cookies
from mitmproxy.test import taddons
from mitmproxy.test import tutils
from mitmproxy.connection import Server
from mitmproxy.exceptions import CommandError
from mitmproxy.http import Headers
from mitmproxy.http import Request
from mitmproxy.http import Response
from mitmproxy.test import tflow
from wsproto.frame_protocol import Opcode
from mitmproxy.websocket import WebSocketMessage
from mitmproxy.test.tflow import ttcpflow



test_dir = Path(__file__).parent.parent
mitmproxy_dir = test_dir.parent.parent

def flow(resp_content=b"message"):
    times = dict(
        timestamp_start=746203272,
        timestamp_end=746203272,
    )

    # Create a dummy flow for testing
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

    assert s.flow_entry(flow, set())["timings"]["send"] == 1

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
        Path(test_dir / f"data/flows/{log_file.stem}.har").read_bytes()
    )
    actual_har = json.loads(Path(tmp_path / "testing_flow.har").read_bytes())

    assert actual_har == expected_har



def test_savehar_dump(tmpdir, tdata):

        with taddons.context() as tctx:

            a = tctx.script(tdata.path("../mitmproxy/addons/savehar.py"))
            assert a
            path = str(tmpdir.join("somefile"))
            tctx.configure(a, hardump=path)
            
            for x in io.read_flows_from_paths([Path(test_dir / "data/flows/websocket.mitm")]):
                
                a.websocket_end(x)
            a.done()

            with open(path) as inp:
                har = json.load(inp)
                har["log"]["creator"]["comment"] = 'mitmproxy version 1.2.3'
            assert har == json.loads(Path(test_dir / f"data/flows/websocket.har").read_bytes())

def test_options( tdata, capfd):

        with taddons.context() as tctx:

            a = tctx.script(tdata.path("../mitmproxy/addons/savehar.py"))
            assert a
            tctx.configure(a, hardump="-")
            
            for x in io.read_flows_from_paths([Path(test_dir / "data/flows/websocket.mitm")]):
                a.websocket_end(x)
            a.done()
            out, _ = capfd.readouterr()
            out_har = json.loads(out)
            out_har['log']['creator']['comment'] = 'mitmproxy version 1.2.3'
            assert out_har == json.loads(Path(test_dir / f"data/flows/websocket.har").read_bytes())

def test_zhar(tmpdir, tdata):

        with taddons.context() as tctx:

            a = tctx.script(tdata.path("../mitmproxy/addons/savehar.py"))
            assert a
            path = str(tmpdir.join("somefile.zhar"))
            tctx.configure(a, hardump=path)
            
            for x in io.read_flows_from_paths([Path(test_dir / "data/flows/successful_log.mitm")]):
                a.websocket_end(x)
            a.done()

        with open(path, 'rb') as inp:

            try:
                decompressed_data = zlib.decompress(inp.read())
                har = json.loads(decompressed_data.decode())
            except zlib.error as e:

                print(f"Error decompressing: {e}")
                har = None
                
        if har:
            har["log"]["creator"]["comment"] = 'mitmproxy version 1.2.3'

      
        expected_path = test_dir / "data/flows/compressed.zhar"
        with open(expected_path, 'rb') as expected_file:

            try:
                decompressed_expected = zlib.decompress(expected_file.read())
                expected_data = json.loads(decompressed_expected.decode())
            except zlib.error as e:
                
                print(f"Error decompressing: {e}")
                expected_data = None
            if expected_data:
                expected_data["log"]["creator"]["comment"] = 'mitmproxy version 1.2.3'

        
        assert har == expected_data


def test_base64(tmpdir, tdata):
    with taddons.context() as tctx:
        a = tctx.script(tdata.path("../mitmproxy/addons/savehar.py"))
        assert a
        path = str(tmpdir.join("somefile"))
        tctx.configure(a, hardump=path)

        a.response(flow(resp_content=b"foo" + b"\xFF" * 10))
        a.done()
        with open(path) as inp:
            har = json.load(inp)
        assert (
            har["log"]["entries"][0]["response"]["content"]["encoding"] == "base64"
        )


if __name__ == "__main__":
    s = SaveHar()
    setattr(version, "VERSION", "1.2.3")
    for file in test_dir.glob("data/flows/*.mitm"):
        if not file.suffix == ".har":
            path = open(file, "rb")
            flows = list(io.FlowReader(path).stream())
            s.export_har(flows, types.Path(test_dir / f"data/flows/{file.stem}.har"))
    
    # Loads compressed har file
    with taddons.context() as tctx:

        a = tctx.script(str(mitmproxy_dir / "mitmproxy/addons/savehar.py"))
        assert a
    
        tctx.configure(a, hardump="test/mitmproxy/data/flows/compressed.zhar")
        
        for x in io.read_flows_from_paths([Path(test_dir / "data/flows/successful_log.mitm")]):
            a.websocket_end(x)
        a.done()   
