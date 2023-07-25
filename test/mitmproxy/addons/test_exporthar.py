import json
from pathlib import Path

import pytest

from mitmproxy import io
from mitmproxy import types
from mitmproxy.addons.exporthar import ExportHar
from mitmproxy.http import Headers
from mitmproxy.http import Request
from mitmproxy.http import Response


here = Path(__file__).parent.parent.absolute()


def test_write_errors():
    e = ExportHar()

    with pytest.raises(FileNotFoundError):
        e.export_har([], types.Path("unknown_dir/testing_flow.har"))


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


@pytest.mark.parametrize(
    "log_file", [pytest.param(x, id=x.stem) for x in here.glob("data/flows/*.mitm")]
)
def test_exporthar(log_file: Path, tmp_path: Path):
    e = ExportHar()

    flows = io.read_flows_from_paths([log_file])

    e.export_har(flows, types.Path(tmp_path / "testing_flow.har"))
    correct_har = json.load(open(f"data/flows/{log_file.stem}.har"))
    testing_har = json.load(open(tmp_path / "testing_flow.har"))

    assert testing_har == correct_har


if __name__ == "__main__":
    e = ExportHar()
    print(here)
    for file in here.glob("data/flows/*"):
        if not file.suffix == ".har":
            path = open(file, "rb")
            flows = io.FlowReader(path).stream()

            e.export_har(flows, types.Path(f"data/flows/{file.stem}.har"))
