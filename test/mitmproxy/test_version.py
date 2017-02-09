import runpy

from mitmproxy import version


def test_version(capsys):
    runpy.run_module('mitmproxy.version', run_name='__main__')
    stdout, stderr = capsys.readouterr()
    assert len(stdout) > 0
    assert stdout.strip() == version.VERSION
