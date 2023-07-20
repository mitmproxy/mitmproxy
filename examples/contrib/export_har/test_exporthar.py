import json
from pathlib import Path

import pytest
from exporthar import ExportHar

from mitmproxy import io
from mitmproxy import types

here = Path(__file__).parent.absolute()


@pytest.mark.parametrize("log_file", [pytest.param(here / "flows/logfile", id="logfile")])
def test_errors(log_file):
    e = ExportHar()
    path = open(log_file, "rb")
    flows = io.FlowReader(path).stream()
    pytest.raises(
        FileNotFoundError,
        e.export_har,
        flows,
        types.Path("unknown_dir/testing_flow.har"),
    )


@pytest.mark.parametrize("log_file", [pytest.param(here / "flows/logfile", id="logfile")])
def test_exporthar(log_file, tmp_path):
    e = ExportHar()
    path = open(log_file, "rb")
    flows = io.FlowReader(path).stream()
    e.export_har(flows, types.Path(tmp_path / "testing_flow.har"))
    correct_har = json.load(open("flows/correct_flows.har"))
    testing_har = json.load(open(tmp_path / "testing_flow.har"))

    assert testing_har == correct_har


if __name__ == "__main__":
    e = ExportHar()
    path = open(here / "flows/logfile", "rb")
    flows = io.FlowReader(path).stream()
    e.export_har(flows, types.Path(here / "flows/correct_flows.har"))
