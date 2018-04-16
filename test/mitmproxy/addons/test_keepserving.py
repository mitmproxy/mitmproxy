import asyncio
import pytest

from mitmproxy.addons import keepserving
from mitmproxy.test import taddons


@pytest.mark.asyncio
async def test_keepserving():
    ks = keepserving.KeepServing()
    with taddons.context(ks) as tctx:
        ks.event_processing_complete()
        asyncio.sleep(0.1)
        assert tctx.master.should_exit.is_set()
