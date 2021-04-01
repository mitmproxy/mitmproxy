import pytest
from mitmproxy.utils.spec import parse_spec


def test_parse_spec():
    flow_filter, subject, replacement = parse_spec("/foo/bar/voing")
    assert flow_filter.pattern == "foo"
    assert subject == "bar"
    assert replacement == "voing"

    flow_filter, subject, replacement = parse_spec("/bar/voing")
    assert flow_filter(1) is True
    assert subject == "bar"
    assert replacement == "voing"

    with pytest.raises(ValueError, match="Invalid number of parameters"):
        parse_spec("/")

    with pytest.raises(ValueError, match="Invalid filter pattern"):
        parse_spec("/~b/one/two")
