import pytest

from mitmproxy.contentviews import json_view
from mitmproxy.contentviews import Metadata


def test_view_json():
    meta = Metadata()
    assert json_view.prettify(b"null", meta)
    assert json_view.prettify(b"{}", meta)
    with pytest.raises(ValueError):
        assert not json_view.prettify(b"{", meta)
    assert json_view.prettify(b"[1, 2, 3, 4, 5]", meta)
    assert json_view.prettify(b'{"foo" : 3}', meta)
    assert json_view.prettify(b'{"foo": true, "nullvalue": null}', meta)
    assert json_view.prettify(b"[]", meta)
    assert json_view.syntax_highlight == "yaml"


def test_render_priority():
    assert json_view.render_priority(b"data", Metadata(content_type="application/json"))
    assert json_view.render_priority(
        b"data", Metadata(content_type="application/json-rpc")
    )
    assert json_view.render_priority(
        b"data", Metadata(content_type="application/vnd.api+json")
    )
    assert json_view.render_priority(
        b"data", Metadata(content_type="application/acme+json")
    )
    assert not json_view.render_priority(b"data", Metadata(content_type="text/plain"))
    assert not json_view.render_priority(b"", Metadata(content_type="application/json"))
