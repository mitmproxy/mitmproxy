import asyncio

import pytest

from mitmproxy import log
from mitmproxy.addons.errorcheck import ErrorCheck


@pytest.mark.parametrize("do_log", [True, False])
def test_errorcheck(capsys, do_log):
    async def run():
        # suppress error that task exception was not retrieved.
        asyncio.get_running_loop().set_exception_handler(lambda *_: 0)
        e = ErrorCheck(do_log)
        e.add_log(log.LogEntry("fatal", "error"))
        await e.running()
        await asyncio.sleep(0)

    with pytest.raises(SystemExit):
        asyncio.run(run())

    if do_log:
        assert capsys.readouterr().err == "Error on startup: fatal\n"


async def test_no_error():
    e = ErrorCheck()
    await e.running()
    await asyncio.sleep(0)
