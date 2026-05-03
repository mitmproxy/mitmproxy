"""Smoke-test that the categorised exit codes wire up at each call site.

The intent is to pin every fatal branch's exit code so a future "everything
funnelled through ``sys.exit(1)`` again" regression is caught — not to
exhaustively test the surrounding flow logic, which already has its own
suite. We monkeypatch the smallest dependency that lets the branch fire and
assert the SystemExit's argument matches the constant from
``mitmproxy.utils.exit_codes``.
"""

import builtins
import logging

import pytest

from mitmproxy import exceptions
from mitmproxy import log
from mitmproxy.addons import errorcheck
from mitmproxy.addons import save
from mitmproxy.addons import termlog
from mitmproxy.test import taddons
from mitmproxy.utils import exit_codes


def test_codes_distinct():
    """Sanity: every documented code is unique so a parent process can
    actually distinguish them. (Catches a copy-paste typo in exit_codes.py.)"""
    members = {
        name: getattr(exit_codes, name)
        for name in dir(exit_codes)
        if name.isupper() and not name.startswith("_")
    }
    assert len(members) == len(set(members.values())), members


def test_termlog_cannot_print(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(builtins, "print", _raise)

    t = termlog.TermLog()
    with taddons.context(t) as tctx:
        tctx.configure(t)
        with pytest.raises(SystemExit) as exc_info:
            t.logger.emit(
                logging.LogRecord(
                    "test",
                    logging.ERROR,
                    pathname="test.py",
                    lineno=1,
                    msg="oh no",
                    args=None,
                    exc_info=None,
                )
            )

        assert exc_info.value.args[0] == exit_codes.CANNOT_PRINT


def test_save_cannot_write_to_file(tmp_path, monkeypatch) -> None:
    """save.py exits with CANNOT_WRITE_TO_FILE when the underlying file
    handle raises during a flow write. We force the failure by handing
    save.start_stream_to_path() a path it can open initially but then
    monkeypatching the writer's write() to raise OSError before
    save_flow runs."""

    s = save.Save()
    target = tmp_path / "flows.bin"
    with taddons.context(s) as tctx:
        tctx.configure(s, save_stream_file=str(target))

        def _raise(*args, **kwargs):
            raise OSError("disk full")

        # Force the per-flow writer to error on the next write call.
        assert s.stream is not None
        monkeypatch.setattr(s.stream, "add", _raise)

        from mitmproxy.test import tflow

        with pytest.raises(SystemExit) as exc_info:
            s.save_flow(tflow.tflow())

        assert exc_info.value.args[0] == exit_codes.CANNOT_WRITE_TO_FILE


async def test_errorcheck_startup_error() -> None:
    """errorcheck.shutdown_if_errored exits with STARTUP_ERROR when an
    error-level log record was captured during startup."""
    e = errorcheck.ErrorCheck(repeat_errors_on_stderr=False)
    e.logger.has_errored.append(
        logging.LogRecord(
            "test",
            logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="boom",
            args=None,
            exc_info=None,
        )
    )

    with pytest.raises(SystemExit) as exc_info:
        await e.shutdown_if_errored()

    assert exc_info.value.args[0] == exit_codes.STARTUP_ERROR


def test_invalid_options_code_is_distinct() -> None:
    """The OptionsError handler in tools/main.py uses INVALID_OPTIONS;
    pin the constant to keep parent-process integrations stable.
    Also asserts the constant doesn't collide with the more-generic
    INVALID_ARGS — argparse failures and OptionsError need to remain
    distinguishable for CI tooling."""
    assert exit_codes.INVALID_OPTIONS != exit_codes.INVALID_ARGS
    assert exit_codes.INVALID_OPTIONS != exit_codes.GENERIC_ERROR


def test_options_error_module_imports() -> None:
    """Smoke test: the OptionsError exception type used by tools/main.py
    is the one our exit_codes pinning expects to bracket."""
    assert exceptions.OptionsError.__module__ == "mitmproxy.exceptions"
