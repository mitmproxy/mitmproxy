from mitmproxy.utils import data
from . import tutils


def test_pkg_data():
    assert data.pkg_data.path("tools/console")
    tutils.raises("does not exist", data.pkg_data.path, "nonexistent")
