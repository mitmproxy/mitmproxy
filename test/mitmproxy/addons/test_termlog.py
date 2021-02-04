import sys
import pytest

from mitmproxy.addons import termlog
from mitmproxy import log
from mitmproxy.test import taddons


class TestTermLog:
    @pytest.mark.usefixtures('capfd')
    @pytest.mark.parametrize('outfile, expected_out, expected_err', [
        (None, ['one', 'three'], ['four']),
        (sys.stdout, ['one', 'three', 'four'], []),
        (sys.stderr, [], ['one', 'three', 'four']),
    ])
    def test_output(self, outfile, expected_out, expected_err, capfd):
        t = termlog.TermLog(outfile=outfile)
        with taddons.context(t) as tctx:
            tctx.options.termlog_verbosity = "info"
            tctx.configure(t)
            t.add_log(log.LogEntry("one", "info"))
            t.add_log(log.LogEntry("two", "debug"))
            t.add_log(log.LogEntry("three", "warn"))
            t.add_log(log.LogEntry("four", "error"))
        out, err = capfd.readouterr()
        assert out.strip().splitlines() == expected_out
        assert err.strip().splitlines() == expected_err
