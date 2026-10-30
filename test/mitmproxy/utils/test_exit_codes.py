import sys

import pytest

from mitmproxy.utils import exit_codes
from mitmproxy.utils.exit_codes import ExitCode


def test_exit_codes_constants():
    assert exit_codes.SUCCESS == ExitCode.SUCCESS == 0
    assert exit_codes.GENERIC_ERROR == ExitCode.GENERIC_ERROR == 1
    assert exit_codes.STARTUP_ERROR == ExitCode.STARTUP_ERROR == 10
    assert exit_codes.NO_UTF_CONSOLE == ExitCode.NO_UTF_CONSOLE == 20
    assert exit_codes.NO_TTY == ExitCode.NO_TTY == 21
    assert exit_codes.INVALID_ARGS == ExitCode.INVALID_ARGS == 30
    assert exit_codes.INVALID_OPTIONS == ExitCode.INVALID_OPTIONS == 31
    assert exit_codes.CANNOT_PRINT == ExitCode.CANNOT_PRINT == 40
    assert exit_codes.CANNOT_WRITE_TO_FILE == ExitCode.CANNOT_WRITE_TO_FILE == 41


def test_exit_codes_are_unique():
    values = [member.value for member in ExitCode]
    assert len(values) == len(set(values))


def test_exit_codes_int_compatibility():
    for member in ExitCode:
        assert isinstance(member, int)
        assert member == member.value


@pytest.mark.parametrize("code", list(ExitCode))
def test_sys_exit_with_exit_code(code):
    with pytest.raises(SystemExit) as exc_info:
        sys.exit(code)
    assert exc_info.value.code == code
    assert exc_info.value.code == code.value
