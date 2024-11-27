import logging

import pytest

from mitmproxy.addons.errorcheck import ErrorCheck
from mitmproxy.tools import main


@pytest.mark.parametrize("run_main", [main.mitmdump, main.mitmproxy])
def test_errorcheck(tdata, capsys, run_main):
    """Integration test: Make sure that we catch errors on startup an exit."""
    with pytest.raises(SystemExit):
        run_main(
            [
                "-n",
                "-s",
                tdata.path("mitmproxy/data/addonscripts/load_error.py"),
            ]
        )
    assert "Error logged during startup" in capsys.readouterr().err


async def test_no_error():
    e = ErrorCheck()
    await e.shutdown_if_errored()
    e.finish()


async def test_error_message(capsys):
    e = ErrorCheck()
    logging.error("wat")
    logging.error("wat")
    with pytest.raises(SystemExit):
        await e.shutdown_if_errored()
    assert "Errors logged during startup, exiting..." in capsys.readouterr().err


async def test_repeat_error_on_stderr(capsys):
    e = ErrorCheck(repeat_errors_on_stderr=True)
    logging.error("wat")
    with pytest.raises(SystemExit):
        await e.shutdown_if_errored()
    assert "Error logged during startup:\nwat" in capsys.readouterr().err
