import io
import os
import sys
from unittest import mock

import pytest

from mitmproxy.utils import debug
from mitmproxy.utils import exit_codes


@pytest.mark.parametrize("precompiled", [True, False])
def test_dump_system_info_precompiled(precompiled):
    sys.frozen = None
    with mock.patch.object(sys, "frozen", precompiled):
        assert ("binary" in debug.dump_system_info()) == precompiled


def test_dump_info():
    cs = io.StringIO()
    debug.dump_info(None, None, file=cs)
    assert cs.getvalue()
    assert "Tasks" not in cs.getvalue()


def test_dump_info_debug_exit(monkeypatch):
    def _true(*_):
        return True

    monkeypatch.setattr(os, "getenv", _true)

    with pytest.raises(SystemExit) as excinfo:
        cs = io.StringIO()
        debug.dump_info(None, None, file=cs)

    assert excinfo.value.code == exit_codes.GENERIC_ERROR


async def test_dump_info_async():
    cs = io.StringIO()
    debug.dump_info(None, None, file=cs)
    assert "Tasks" in cs.getvalue()


def test_dump_stacks():
    cs = io.StringIO()
    debug.dump_stacks(None, None, file=cs)
    assert cs.getvalue()


def test_dump_stacks_debug_exit(monkeypatch):
    def _true(*_):
        return True

    monkeypatch.setattr(os, "getenv", _true)

    with pytest.raises(SystemExit) as excinfo:
        cs = io.StringIO()
        debug.dump_stacks(None, None, file=cs)

    assert excinfo.value.code == exit_codes.GENERIC_ERROR


def test_register_info_dumpers():
    debug.register_info_dumpers()
