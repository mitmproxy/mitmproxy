import io
import json
from pathlib import Path

import pytest

from mitmproxy import exceptions
from mitmproxy.io import FlowReader
from mitmproxy.io.har import fix_headers
from mitmproxy.io.har import request_to_flow
from mitmproxy.tools.web.app import flow_to_json

data_dir = Path(__file__).parent.parent / "data"

form_urlencoded_header = [
    {"name": "Content-Type", "value": "application/x-www-form-urlencoded"}
]

# Ordered form fields covering duplicates, blank values, spaces, reserved
# characters and non-ASCII text. Non-ASCII is spelled with escapes so that the
# fixture stays pure ASCII while still exercising UTF-8 percent-encoding.
urlencoded_params = [
    {"name": "b", "value": "2"},
    {"name": "a", "value": "1"},
    {"name": "a", "value": "1"},
    {"name": "blank", "value": ""},
    {"name": "spaced name", "value": "1 2"},
    {"name": "plus+amp", "value": "a&b=c/d?e#f"},
    {"name": "unicode", "value": "gr\u00fc\u00dfe \u2603"},
]

urlencoded_params_expected = [
    ("b", "2"),
    ("a", "1"),
    ("a", "1"),
    ("blank", ""),
    ("spaced name", "1 2"),
    ("plus+amp", "a&b=c/d?e#f"),
    ("unicode", "gr\u00fc\u00dfe \u2603"),
]

urlencoded_wire = (
    b"b=2&a=1&a=1&blank=&spaced+name=1+2"
    b"&plus%2Bamp=a%26b%3Dc%2Fd%3Fe%23f"
    b"&unicode=gr%C3%BC%C3%9Fe+%E2%98%83"
)


def make_har_entry(post_data: dict | None, headers: list[dict[str, str]]) -> dict:
    """Minimal well-formed HAR entry, with optional request postData."""
    request: dict = {
        "method": "POST",
        "url": "http://example.invalid/submit",
        "httpVersion": "HTTP/1.1",
        "headers": headers,
    }
    if post_data is not None:
        request["postData"] = post_data
    return {
        "startedDateTime": "2026-01-01T00:00:00.000Z",
        "time": 10.0,
        "request": request,
        "response": {
            "status": 200,
            "httpVersion": "HTTP/1.1",
            "headers": [],
            "content": {"size": 0, "mimeType": "text/plain", "text": ""},
        },
    }


def read_har_flows(entries: list[dict]) -> list:
    """Reads a HAR file with the given entries through the public FlowReader."""
    har_bytes = json.dumps({"log": {"version": "1.2", "entries": entries}}).encode()
    return list(FlowReader(io.BytesIO(har_bytes)).stream())


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


def test_urlencoded_form_params_only():
    entry = make_har_entry(
        {"mimeType": "application/x-www-form-urlencoded", "params": urlencoded_params},
        form_urlencoded_header,
    )

    flow = request_to_flow(entry)

    assert flow.request.content == urlencoded_wire
    assert list(flow.request.urlencoded_form.items(multi=True)) == (
        urlencoded_params_expected
    )


def test_urlencoded_form_params_only_through_flowreader():
    entry = make_har_entry(
        {"mimeType": "application/x-www-form-urlencoded", "params": urlencoded_params},
        form_urlencoded_header,
    )

    flows = read_har_flows([entry])

    assert len(flows) == 1
    assert flows[0].request.content == urlencoded_wire
    assert list(flows[0].request.urlencoded_form.items(multi=True)) == (
        urlencoded_params_expected
    )


@pytest.mark.parametrize(
    "mime_type",
    [
        "application/x-www-form-urlencoded; charset=UTF-8",
        "Application/X-WWW-Form-Urlencoded",
    ],
)
def test_urlencoded_form_params_mime_type_variants(mime_type):
    entry = make_har_entry(
        {"mimeType": mime_type, "params": [{"name": "k", "value": "v v"}]},
        form_urlencoded_header,
    )

    flow = request_to_flow(entry)

    assert flow.request.content == b"k=v+v"
    assert list(flow.request.urlencoded_form.items(multi=True)) == [("k", "v v")]


def test_urlencoded_form_params_empty_list():
    entry = make_har_entry(
        {"mimeType": "application/x-www-form-urlencoded", "params": []},
        form_urlencoded_header,
    )

    flow = request_to_flow(entry)

    assert flow.request.content == b""
    assert list(flow.request.urlencoded_form.items(multi=True)) == []


def test_post_data_text_takes_precedence_over_params():
    entry = make_har_entry(
        {
            "mimeType": "application/x-www-form-urlencoded",
            "text": "from=text",
            "params": [{"name": "from", "value": "params"}],
        },
        form_urlencoded_header,
    )

    flow = request_to_flow(entry)

    assert flow.request.content == b"from=text"
    assert list(flow.request.urlencoded_form.items(multi=True)) == [("from", "text")]


def test_post_data_empty_text_takes_precedence_over_params():
    entry = make_har_entry(
        {
            "mimeType": "application/x-www-form-urlencoded",
            "text": "",
            "params": [{"name": "from", "value": "params"}],
        },
        form_urlencoded_header,
    )

    flow = request_to_flow(entry)

    assert flow.request.content == b""
    assert list(flow.request.urlencoded_form.items(multi=True)) == []


def test_post_data_text_only_json_body_is_unchanged():
    entry = make_har_entry(
        {"mimeType": "application/json", "text": '{"a": 1}'},
        [{"name": "Content-Type", "value": "application/json"}],
    )

    flow = request_to_flow(entry)

    assert flow.request.content == b'{"a": 1}'


def test_request_without_post_data_has_empty_body():
    entry = make_har_entry(None, [])

    flow = request_to_flow(entry)

    assert flow.request.content == b""


def test_urlencoded_form_params_blank_name_and_blank_value():
    entry = make_har_entry(
        {
            "mimeType": "application/x-www-form-urlencoded",
            "params": [
                {"name": "", "value": "v"},
                {"name": "k", "value": ""},
            ],
        },
        form_urlencoded_header,
    )

    flow = request_to_flow(entry)

    assert flow.request.content == b"=v&k="
    assert list(flow.request.urlencoded_form.items(multi=True)) == [
        ("", "v"),
        ("k", ""),
    ]


def test_flowreader_imports_forms_after_text_only_entries():
    entries = [
        make_har_entry(
            {"mimeType": "application/json", "text": '{"n": 1}'},
            [{"name": "Content-Type", "value": "application/json"}],
        ),
        make_har_entry(
            {
                "mimeType": "application/x-www-form-urlencoded",
                "params": urlencoded_params,
            },
            form_urlencoded_header,
        ),
        make_har_entry(
            {"mimeType": "text/plain", "text": "done"},
            [{"name": "Content-Type", "value": "text/plain"}],
        ),
    ]

    flows = read_har_flows(entries)

    assert [flow.request.content for flow in flows] == [
        b'{"n": 1}',
        urlencoded_wire,
        b"done",
    ]


@pytest.mark.parametrize(
    "post_data_extra",
    [
        pytest.param({}, id="mimeType-absent"),
        pytest.param({"mimeType": "application/json"}, id="mimeType-unrelated"),
    ],
)
def test_params_only_with_unsupported_mime_type_is_still_rejected(post_data_extra):
    post_data = {**post_data_extra, "params": [{"name": "field", "value": "value"}]}
    entry = make_har_entry(post_data, form_urlencoded_header)

    with pytest.raises(KeyError):
        request_to_flow(entry)


def test_params_only_non_form_mime_type_is_still_rejected():
    # No fake multipart/file support: unchanged exception behavior.
    entry = make_har_entry(
        {
            "mimeType": "multipart/form-data",
            "params": [{"name": "field", "value": "value"}],
        },
        [{"name": "Content-Type", "value": "multipart/form-data; boundary=x"}],
    )

    with pytest.raises(KeyError):
        request_to_flow(entry)


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


if __name__ == "__main__":
    for path_name in data_dir.glob("har_files/*.har"):
        print(path_name)

        flows = file_to_flows(path_name)

        with open(data_dir / f"har_files/{path_name.stem}.json", "w") as f:
            json.dump(flows, f, indent=4)
