import os
import tempfile

from mitmproxy.tools.console import master


def test_try_unlink_file_not_exists():
    path = os.path.join(tempfile.mkdtemp(), 'something')
    assert not os.path.exists(path)
    master.try_unlink(path)
