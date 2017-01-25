import io
import subprocess
from unittest import mock

from mitmproxy.utils import debug


def test_dump_system_info():
    assert debug.dump_system_info()

    with mock.patch('subprocess.check_output') as m:
        m.side_effect = subprocess.CalledProcessError(-1, 'git describe --tags --long')
        assert 'release version' in debug.dump_system_info()


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
