from mitmproxy.utils import exit_codes


def test_exit_codes_are_distinct():
    """All non-zero exit codes should be unique."""
    codes = [
        exit_codes.GENERIC_ERROR,
        exit_codes.STARTUP_ERROR,
        exit_codes.NO_TTY,
        exit_codes.INVALID_ARGS,
        exit_codes.INVALID_OPTIONS,
        exit_codes.CANNOT_PRINT,
        exit_codes.CANNOT_WRITE_TO_FILE,
    ]
    assert len(codes) == len(set(codes))


def test_success_is_zero():
    assert exit_codes.SUCCESS == 0
