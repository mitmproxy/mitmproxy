import io
import sys
from unittest import mock
import pytest

from mitmproxy.utils import debug


@pytest.mark.parametrize("precompiled", [True, False])
def test_dump_system_info_precompiled(precompiled):
    sys.frozen = None
    with mock.patch.object(sys, 'frozen', precompiled):
        assert ("binary" in debug.dump_system_info()) == precompiled


def test_dump_info():
    cs = io.StringIO()
    debug.dump_info(None, None, file=cs, testing=True)
    assert cs.getvalue()
    assert "Tasks" not in cs.getvalue()


@pytest.mark.asyncio
async def test_dump_info_async():
    cs = io.StringIO()
    debug.dump_info(None, None, file=cs, testing=True)
    assert "Tasks" in cs.getvalue()


def test_dump_stacks():
    cs = io.StringIO()
    debug.dump_stacks(None, None, file=cs, testing=True)
    assert cs.getvalue()


def test_register_info_dumpers():
    debug.register_info_dumpers()
