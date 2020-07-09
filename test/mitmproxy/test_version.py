import pathlib
import runpy
import subprocess
import sys
from unittest import mock

from mitmproxy import version


def test_version(capsys):
    here = pathlib.Path(__file__).absolute().parent
    version_file = here / ".." / ".." / "mitmproxy" / "version.py"
    runpy.run_path(str(version_file), run_name='__main__')
    stdout, stderr = capsys.readouterr()
    assert len(stdout) > 0
    assert stdout.strip() == version.VERSION


def test_get_version():
    version.VERSION = "3.0.0rc2"

    with mock.patch('subprocess.check_output') as m:
        m.return_value = b"tag-0-cafecafe"
        assert version.get_dev_version() == "3.0.0rc2"

        sys.frozen = True
        assert version.get_dev_version() == "3.0.0rc2 binary"
        sys.frozen = False

        m.return_value = b"tag-2-cafecafe"
        assert version.get_dev_version() == "3.0.0rc2 (+2, commit cafecaf)"

        m.side_effect = subprocess.CalledProcessError(-1, 'git describe --tags --long')
        assert version.get_dev_version() == "3.0.0rc2"
