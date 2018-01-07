import pathlib
import runpy
import subprocess
from unittest import mock

from mitmproxy import version


def test_version(capsys):
    here = pathlib.Path(__file__).absolute().parent
    version_file = here / ".." / ".." / "mitmproxy" / "version.py"
    runpy.run_path(str(version_file), run_name='__main__')
    stdout, stderr = capsys.readouterr()
    assert len(stdout) > 0
    assert stdout.strip() == version.VERSION


def test_get_version_hardcoded():
    version.VERSION = "3.0.0.dev123-0xcafebabe"
    assert version.get_version() == "3.0.0"
    assert version.get_version(True) == "3.0.0.dev123"
    assert version.get_version(True, True) == "3.0.0.dev123-0xcafebabe"


def test_get_version():
    version.VERSION = "3.0.0"

    with mock.patch('subprocess.check_output') as m:
        m.return_value = b"tag-0-cafecafe"
        assert version.get_version(True, True) == "3.0.0"

        m.return_value = b"tag-2-cafecafe"
        assert version.get_version(True, True) == "3.0.0.dev2-0xcafecaf"

        m.side_effect = subprocess.CalledProcessError(-1, 'git describe --long')
        assert version.get_version(True, True) == "3.0.0"
