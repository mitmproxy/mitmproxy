import pytest

from mitmproxy.tools import main
from mitmproxy.utils import exit_codes

shutdown_script = "mitmproxy/data/addonscripts/shutdown.py"


def test_mitmweb(tdata):
    main.mitmweb(
        [
            "--no-web-open-browser",
            "-s",
            tdata.path(shutdown_script),
            "-q",
            "-p",
            "0",
            "--web-port",
            "0",
        ]
    )


def test_mitmdump(tdata):
    main.mitmdump(
        [
            "-s",
            tdata.path(shutdown_script),
            "-q",
            "-p",
            "0",
        ]
    )


def test_invalid_args():
    with pytest.raises(SystemExit) as exc_info:
        main.mitmdump(["--nonexistent-flag"])
    assert exc_info.value.code == exit_codes.INVALID_ARGS


def test_invalid_options(tdata):
    with pytest.raises(SystemExit) as exc_info:
        main.mitmdump(
            [
                "-s",
                tdata.path(shutdown_script),
                "-q",
                "-p",
                "0",
                "--set",
                "listen_port=abc",
            ]
        )
    assert exc_info.value.code == exit_codes.INVALID_OPTIONS
