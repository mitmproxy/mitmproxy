import json
from pathlib import Path

import pytest
from readhar import ReadHar

from mitmproxy import exceptions
from mitmproxy import types
from mitmproxy.tools.web.app import flow_to_json

here = Path(__file__).parent.absolute()


def file_to_flows(path_name: Path) -> list[dict]:
    r = ReadHar()
    with open(path_name, "rb") as f:
        file_json = json.load(f)["log"]["entries"]
        flows = []

        for entry in file_json:
            expected = r.request_to_flow(entry)
            flow_json = flow_to_json(expected)
            flows.append(flow_json)

    return flows


def test_corrupt():
    r = ReadHar()

    pytest.raises(
        exceptions.CommandError, r.read_har, types.Path("./corrupted/brokenfile.har")
    )
    with open("./corrupted/broken_headers.json") as f:
        file_json = json.load(f)
        pytest.raises(exceptions.OptionsError, r.fix_headers, file_json["headers"])


@pytest.mark.parametrize(
    "har_file", [pytest.param(x, id=x.stem) for x in here.glob("har_files/*.har")]
)
def test_har_to_flow(har_file: Path):
    expected_file = har_file.with_suffix(".json")

    expected_flows = json.loads(expected_file.read_bytes())
    actual_flows = file_to_flows(har_file)

    for expected, actual in zip(expected_flows, actual_flows):
        actual = json.loads(json.dumps(actual))

        actual["id"] = expected["id"]
        actual["timestamp_created"] = expected["timestamp_created"]
        actual["server_conn"]["id"] = expected["server_conn"]["id"]
        actual["client_conn"]["id"] = expected["client_conn"]["id"]

        assert actual == expected


if __name__ == "__main__":
    for path_name in here.glob("har_files/*.har"):
        print(path_name)

        flows = file_to_flows(path_name)

        with open(f"har_files/{path_name.stem}.json", "w") as f:
            json.dump(flows, f, indent=4)
