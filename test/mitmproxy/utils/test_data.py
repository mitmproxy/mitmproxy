import pytest
from mitmproxy.utils import data


def test_pkg_data():
    assert data.pkg_data.path("tools/console")
    with pytest.raises(ValueError):
        data.pkg_data.path("nonexistent")
