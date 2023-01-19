import pytest

from mitmproxy.addons.errorcheck import ErrorCheck
from mitmproxy.tools import main
from mitmproxy.utils import exit_codes


def test_errorcheck(tdata, capsys):
    """Integration test: Make sure that we catch errors on startup an exit."""
    with pytest.raises(SystemExit) as excinfo:
        main.mitmproxy(
            [
                "-s",
                tdata.path("mitmproxy/data/addonscripts/load_error.py"),
            ]
        )
    assert "Error on startup" in capsys.readouterr().err
    assert excinfo.value.code == exit_codes.STARTUP_ERROR


async def test_no_error():
    e = ErrorCheck()
    await e.shutdown_if_errored()
    e.finish()
