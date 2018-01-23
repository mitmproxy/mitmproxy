# TODO: write tests
import pytest
from mitmproxy.contentviews import base


def test_format_dict():
    d = {"one": "two", "three": "four"}
    f_d = base.format_dict(d)
    assert next(f_d)

    d = {"adsfa": ""}
    f_d = base.format_dict(d)
    assert next(f_d)

    d = {}
    f_d = base.format_dict(d)
    with pytest.raises(StopIteration):
        next(f_d)
