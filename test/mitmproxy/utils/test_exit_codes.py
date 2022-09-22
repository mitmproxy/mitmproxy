import builtins
import pytest

from mitmproxy import log
from mitmproxy.addons import termlog, save
from mitmproxy.test import taddons
from mitmproxy.utils import exit_codes


def test_termlog_cannot_print(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise OSError

    monkeypatch.setattr(builtins, "print", _raise)

    t = termlog.TermLog()
    with taddons.context(t) as tctx:
        tctx.configure(t)
        with pytest.raises(SystemExit) as exc_info:
            t.add_log(log.LogEntry("error", "error"))

        assert exc_info.value.args[0] == exit_codes.CANNOT_PRINT
