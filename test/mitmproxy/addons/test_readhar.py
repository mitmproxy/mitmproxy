import json
from pathlib import Path

import pytest
import asyncio
from mitmproxy.addons.readhar import ReadHar

from mitmproxy import exceptions
from mitmproxy import types
from mitmproxy.addons.view import View
from mitmproxy.test import taddons
from mitmproxy.tools.web.app import flow_to_json

here = Path(__file__).parent.parent / "data"


def hardcode_variable_fields_for_tests(flow: dict) -> None:
    flow["id"] = "hardcoded_for_test"
    flow["timestamp_created"] = 0
    flow["server_conn"]["id"] = "hardcoded_for_test"
    flow["client_conn"]["id"] = "hardcoded_for_test"


def file_to_flows(path_name: Path) -> list[dict]:
    r = ReadHar()

    file_json = json.loads(path_name.read_bytes())["log"]["entries"]
    flows = []

    for entry in file_json:
        expected = r.request_to_flow(entry)
        flow_json = flow_to_json(expected)
        hardcode_variable_fields_for_tests(flow_json)
        flows.append(flow_json)

    return flows


def test_corrupt():
    r = ReadHar()

    with pytest.raises(exceptions.CommandError):
        r.read_har(types.Path(here / "corrupted_har/brokenfile.har"))

    file_json = json.loads(
        Path(here / "corrupted_har/broken_headers.json").read_bytes()
    )
    with pytest.raises(exceptions.OptionsError):
        r.fix_headers(file_json["headers"])


@pytest.mark.parametrize(
    "har_file", [pytest.param(x, id=x.stem) for x in here.glob("har_files/*.har")]
)
def test_har_to_flow(har_file: Path):
    expected_file = har_file.with_suffix(".json")

    expected_flows = json.loads(expected_file.read_bytes())
    actual_flows = file_to_flows(har_file)

    for expected, actual in zip(expected_flows, actual_flows):
        actual = json.loads(json.dumps(actual))

        assert actual == expected


@pytest.mark.parametrize(
    "har_file", [pytest.param(x, id=x.stem) for x in here.glob("har_files/*.har")]
)
async def test_read_har(har_file):
    r = ReadHar()
    v = View()
    with taddons.context(r, v):
        assert v.store_count() == 0
        r.read_har(types.Path(har_file))
        await asyncio.sleep(0)
        assert v.store_count() > 0


if __name__ == "__main__":
    for path_name in here.glob("har_files/*.har"):
        print(path_name)

        flows = file_to_flows(path_name)

        with open(f"har_files/{path_name.stem}.json", "w") as f:
            json.dump(flows, f, indent=4)
