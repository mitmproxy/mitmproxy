import asyncio
import inspect
import os
import threading
import time

import pytest

from mitmproxy.script.concurrent import run_in_thread
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestConcurrent:
    @pytest.mark.parametrize(
        "addon", ["concurrent_decorator.py", "concurrent_decorator_class.py"]
    )
    async def test_concurrent(self, addon, tdata):
        with taddons.context() as tctx:
            sc = tctx.script(tdata.path(f"mitmproxy/data/addonscripts/{addon}"))
            f1, f2 = tflow.tflow(), tflow.tflow()
            start = time.time()
            await asyncio.gather(
                tctx.cycle(sc, f1),
                tctx.cycle(sc, f2),
            )
            end = time.time()
            # This test may fail on overloaded CI systems, increase upper bound if necessary.
            if os.environ.get("CI"):
                assert 0.5 <= end - start
            else:
                assert 0.5 <= end - start < 1

    def test_concurrent_err(self, tdata, caplog):
        with taddons.context() as tctx:
            tctx.script(
                tdata.path("mitmproxy/data/addonscripts/concurrent_decorator_err.py")
            )
            assert "decorator not supported" in caplog.text


async def test_run_in_thread_function():
    event_loop_thread = threading.get_ident()

    @run_in_thread
    def plain(value: str) -> str:
        assert threading.get_ident() != event_loop_thread
        return value.upper()

    assert inspect.iscoroutinefunction(plain)
    assert await plain("value") == "VALUE"


async def test_run_in_thread_generator():
    event_loop_thread = threading.get_ident()

    @run_in_thread
    def generate():
        assert threading.get_ident() != event_loop_thread
        yield "one"
        assert threading.get_ident() != event_loop_thread
        yield "two"

    assert inspect.isasyncgenfunction(generate)
    assert [item async for item in generate()] == ["one", "two"]


@pytest.mark.parametrize("kind", ["coroutine", "async_generator"])
def test_run_in_thread_rejects_async_functions(kind):
    if kind == "coroutine":

        async def function():
            return None

    else:

        async def function():
            yield None

    with pytest.raises(ValueError, match="cannot be used with async functions"):
        run_in_thread(function)
