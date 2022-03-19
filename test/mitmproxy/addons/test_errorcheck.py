import asyncio

import pytest

from mitmproxy import log
from mitmproxy.addons.errorcheck import ErrorCheck


def test_errorcheck():
    async def run():
        # suppress error that task exception was not retrieved.
        asyncio.get_running_loop().set_exception_handler(lambda *_: 0)
        e = ErrorCheck()
        e.add_log(log.LogEntry("fatal", "error"))
        await e.running()
        await asyncio.sleep(0)

    with pytest.raises(SystemExit):
        asyncio.run(run())


async def test_no_error():
    e = ErrorCheck()
    await e.running()
    await asyncio.sleep(0)
