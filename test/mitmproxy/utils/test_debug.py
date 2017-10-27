import io
import subprocess
import sys
from unittest import mock
import pytest

from mitmproxy.utils import debug


@pytest.mark.parametrize("precompiled", [True, False])
def test_dump_system_info_precompiled(precompiled):
    sys.frozen = None
    with mock.patch.object(sys, 'frozen', precompiled):
        assert ("binary" in debug.dump_system_info()) == precompiled


def test_dump_system_info_version():
    with mock.patch('subprocess.check_output') as m:
        m.return_value = b"v2.0.0-0-cafecafe"
        x = debug.dump_system_info()
        assert 'dev' not in x
        assert 'cafecafe' in x

    with mock.patch('subprocess.check_output') as m:
        m.side_effect = subprocess.CalledProcessError(-1, 'git describe --tags --long')
        assert 'dev' not in debug.dump_system_info()


def test_dump_info():
    cs = io.StringIO()
    debug.dump_info(None, None, file=cs, testing=True)
    assert cs.getvalue()


def test_dump_stacks():
    cs = io.StringIO()
    debug.dump_stacks(None, None, file=cs, testing=True)
    assert cs.getvalue()


def test_register_info_dumpers():
    debug.register_info_dumpers()
