import sys
import pytest

from mitmproxy.addons import termlog
from mitmproxy import log
from mitmproxy.tools.dump import Options
from mitmproxy.test import taddons


class TestTermLog:
    @pytest.mark.usefixtures('capfd')
    @pytest.mark.parametrize('outfile, expected_out, expected_err', [
        (None, 'one\nthree\n', 'four\n'),
        (sys.stdout, 'one\nthree\nfour\n', ''),
        (sys.stderr, '', 'one\nthree\nfour\n'),
    ])
    def test_output(self, outfile, expected_out, expected_err, capfd):
        t = termlog.TermLog(outfile=outfile)
        with taddons.context(options=Options(verbosity=2)) as tctx:
            tctx.configure(t)
            t.log(log.LogEntry("one", "info"))
            t.log(log.LogEntry("two", "debug"))
            t.log(log.LogEntry("three", "warn"))
            t.log(log.LogEntry("four", "error"))
        out, err = capfd.readouterr()
        assert out == expected_out
        assert err == expected_err
