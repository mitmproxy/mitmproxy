import io
import json
from pathlib import Path

import pytest

from mitmproxy import exceptions
from mitmproxy.addons.savehar import SaveHar
from mitmproxy.io import FlowReader
from mitmproxy.io.har import fix_headers
from mitmproxy.io.har import request_to_flow
from mitmproxy.test import tflow
from mitmproxy.tools.web.app import flow_to_json

data_dir = Path(__file__).parent.parent / "data"


def hardcode_variable_fields_for_tests(flow: dict) -> None:
    flow["id"] = "hardcoded_for_test"
    flow["timestamp_created"] = 0
    flow["server_conn"]["id"] = "hardcoded_for_test"
    flow["client_conn"]["id"] = "hardcoded_for_test"


def file_to_flows(path_name: Path) -> list[dict]:
    file_json = json.loads(path_name.read_bytes())["log"]["entries"]
    flows = []

    for entry in file_json:
        expected = request_to_flow(entry)
        flow_json = flow_to_json(expected)
        hardcode_variable_fields_for_tests(flow_json)
        flows.append(flow_json)

    return flows


def test_corrupt():
    file_json = json.loads(
        Path(data_dir / "corrupted_har/broken_headers.json").read_bytes()
    )
    with pytest.raises(exceptions.OptionsError):
        fix_headers(file_json["headers"])


@pytest.mark.parametrize(
    "har_file", [pytest.param(x, id=x.stem) for x in data_dir.glob("har_files/*.har")]
)
def test_har_to_flow(har_file: Path):
    expected_file = har_file.with_suffix(".json")

    expected_flows = json.loads(expected_file.read_bytes())
    actual_flows = file_to_flows(har_file)

    for expected, actual in zip(expected_flows, actual_flows):
        actual = json.loads(json.dumps(actual))

        assert actual == expected


@pytest.mark.parametrize("side", ["request", "response"])
@pytest.mark.parametrize(
    "http_version, expected",
    [
        ("HTTP/1.0", "HTTP/1.0"),
        ("http/1.0", "HTTP/1.0"),
        ("HTTP/1.1", "HTTP/1.1"),
        ("http/2.0", "HTTP/2"),
        ("HTTP/2", "HTTP/2"),
        ("HTTP/3", "HTTP/3"),
        ("", "HTTP/1.1"),
    ],
)
def test_http_version(side: str, http_version: str, expected: str):
    entry = {
        "startedDateTime": "2026-01-01T00:00:00Z",
        "time": 1,
        "request": {
            "method": "GET",
            "url": "http://example.com/",
            "headers": [],
            "httpVersion": "HTTP/1.1",
        },
        "response": {
            "status": 200,
            "headers": [],
            "content": {"text": "hello"},
            "httpVersion": "HTTP/1.1",
        },
    }
    entry[side]["httpVersion"] = http_version
    flow = request_to_flow(entry)
    assert getattr(flow, side).http_version == expected
    other_side = "response" if side == "request" else "request"
    assert getattr(flow, other_side).http_version == "HTTP/1.1"


@pytest.mark.parametrize("side", ["request", "response"])
def test_http_10_har_roundtrip(side: str):
    flow = tflow.tflow(resp=True)
    getattr(flow, side).http_version = "HTTP/1.0"
    raw_har = json.dumps(SaveHar().make_har([flow])).encode()
    imported = next(FlowReader(io.BytesIO(raw_har)).stream())
    assert getattr(imported, side).http_version == "HTTP/1.0"
    other_side = "response" if side == "request" else "request"
    assert getattr(imported, other_side).http_version == "HTTP/1.1"


if __name__ == "__main__":
    for path_name in data_dir.glob("har_files/*.har"):
        print(path_name)

        flows = file_to_flows(path_name)

        with open(data_dir / f"har_files/{path_name.stem}.json", "w") as f:
            json.dump(flows, f, indent=4)
