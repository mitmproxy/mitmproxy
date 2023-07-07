import glob
import json

import pytest
from readhar import ReadHar

from mitmproxy import exceptions
from mitmproxy import types
from mitmproxy.tools.web.app import flow_to_json


def file_to_flows(path_name) -> list[dict]:
    r = ReadHar()
    with open(path_name) as f:
        file_json = json.load(f)["log"]["entries"]
        flows = []

        for entry in file_json:
            expected = r.request_to_flow(entry)
            flow_json = flow_to_json(expected)
            flows.append(flow_json)

    return flows


def requests_to_flows(file_list) -> dict[str, list]:
    results = {}
    for path_name in file_list:
        short_path_name = path_name.split("/")[2]
        results[short_path_name] = {"outcome": []}

        flows = file_to_flows(path_name)
        results[short_path_name]["outcome"] = flows

    return results


def data() -> dict:
    expected = {}
    file_list = glob.glob("./expected/*")
    for file in file_list:
        short_path_name = file.split("/")[2]
        with open(file) as fp:
            file_json = json.load(fp)
            expected[short_path_name] = file_json

    return expected


def test_corrupt():
    r = ReadHar()

    pytest.raises(
        exceptions.CommandError, r.read_har, types.Path("./corrupted/brokenfile.har")
    )
    with open("./corrupted/broken_headers.json") as f:
        file_json = json.load(f)
        pytest.raises(exceptions.OptionsError, r.fix_headers, file_json["headers"])


def test_har_to_flow():
    expected_data = data()
    file_list = glob.glob("./har_files/*.har")
    outcome = requests_to_flows(file_list)

    for file in expected_data:
        index = 0
        for flow in expected_data[file]["outcome"]:
            outcomeflow = outcome[file]["outcome"][index]
            flow = json.loads(json.dumps(flow))
            outcomeflow = json.loads(json.dumps(outcomeflow))

            # TODO figure out why contentHash is changing
            flow["request"].pop("contentHash")
            outcomeflow["request"].pop("contentHash")
            flow["response"].pop("contentHash")
            outcomeflow["response"].pop("contentHash")

            # Perform assertions without comparing 'contentHash'
            assert flow["request"] == outcomeflow["request"]
            assert flow["response"] == outcomeflow["response"]

            index += 1


if __name__ == "__main__":
    pytest.main()
