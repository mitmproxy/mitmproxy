import typing
from subprocess import Popen
import time
import json
from urllib.request import Request, urlopen
import pytest
from mitmproxy import http, ctx


@pytest.fixture(scope="module")
def mitm(tmpdir_factory):
    tmpdir = tmpdir_factory.mktemp("mitm")
    with open(tmpdir / "config.yaml", "w") as f:
        f.write(_YAML_CONFIG)
    mitmdump = Popen([
        "mitmdump",
        "--set", "confdir=" + str(tmpdir),
        "--scripts", __file__,
    ])
    time.sleep(5)
    yield None
    mitmdump.terminate()
    mitmdump.wait()


@pytest.fixture
def mitm_request(mitm, request):
    req = Request("http://mitmproxy.org/" + request.function.__name__)
    req.set_proxy("localhost:8080", "http")
    yield req


class OptionsE2ETestAddon:
    def __init__(self):
        self._e2e_test_str = None
        self._e2e_test_str_seq = ()

    def load(self, loader):
        loader.add_option(
            "e2e_test_str",
            typing.Optional[str],
            self._e2e_test_str,
            "optional str test option"
        )
        loader.add_option(
            "e2e_test_str_seq",
            typing.Sequence[str],
            self._e2e_test_str_seq,
            "str seq test option"
        )

    def request(self, flow):
        if flow.request.pretty_url == "http://mitmproxy.org/test_addons_config_read_correctly":
            results = {
                "e2e_test_str": self._e2e_test_str,
                "e2e_test_str_seq": self._e2e_test_str_seq
            }
            flow.response = http.Response.make(
                200,
                bytes(json.dumps(results), "UTF-8"),
                {"Content-Type": "application/json"}
            )

    def configure(self, updated):
        if "e2e_test_str" in updated:
            self._e2e_test_str = ctx.options.e2e_test_str
            self._e2e_test_str_seq = ctx.options.e2e_test_str_seq


_YAML_CONFIG = """
e2e_test_str: e2e_test_str_value
e2e_test_str_seq: [
    value1,
    value2
]
"""


def test_addons_config_read_correctly(mitm_request):
    expected = {
        "e2e_test_str": "e2e_test_str_value",
        "e2e_test_str_seq": [
            "value1",
            "value2",
        ],
    }
    with urlopen(mitm_request) as r:
        results = json.load(r)
    assert results == expected


addons = [OptionsE2ETestAddon()]
