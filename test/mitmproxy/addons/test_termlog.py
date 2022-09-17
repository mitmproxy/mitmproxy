import asyncio
import io
import logging

import pytest

from mitmproxy.addons import termlog
from mitmproxy.test import taddons
from mitmproxy.utils import vt_codes


@pytest.fixture(autouse=True)
def ensure_cleanup():
    yield
    assert not any(
        isinstance(x, termlog.TermLogHandler)
        for x in logging.root.handlers
    )


async def test_delayed_teardown():
    t = termlog.TermLog()
    t.done()
    assert t.logger in logging.root.handlers
    await asyncio.sleep(0)
    assert t.logger not in logging.root.handlers


def test_output(capsys):
    logging.getLogger().setLevel(logging.DEBUG)
    t = termlog.TermLog()
    with taddons.context(t) as tctx:
        tctx.options.termlog_verbosity = "info"
        tctx.configure(t)
        logging.info("one")
        logging.debug("two")
        logging.warning("three")
        logging.error("four")
    out, err = capsys.readouterr()
    assert "one" in out
    assert "two" not in out
    assert "three" in out
    assert "four" in out
    t.done()


async def test_styling(monkeypatch) -> None:
    monkeypatch.setattr(vt_codes, "ensure_supported", lambda _: True)

    f = io.StringIO()
    t = termlog.TermLog(out=f)
    with taddons.context(t) as tctx:
        tctx.configure(t)
        logging.warning("hello")

    assert "\x1b[33m\x1b[22mhello\x1b[0m" in f.getvalue()
    t.done()
