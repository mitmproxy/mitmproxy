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


def test_view_json_nonascii():
    """https://github.com/mitmproxy/mitmproxy/issues/7739"""
    assert (
        json_view.prettify('{"a": "日本語"}'.encode(), Metadata())
        == '{\n    "a": "日本語"\n}'
    )


def test_view_ndjson():
    meta = Metadata()
    ndjson = b'{"a": 1}\n{"b": [2, 3]}\n'
    assert (
        json_view.prettify(ndjson, meta)
        == '{\n    "a": 1\n}\n{\n    "b": [\n        2,\n        3\n    ]\n}'
    )

    # Empty lines between records are ignored
    ndjson_with_blanks = b'{"a": 1}\n\n  \n{"b": 2}\n'
    assert json_view.prettify(ndjson_with_blanks, meta) == '{\n    "a": 1\n}\n{\n    "b": 2\n}'

    # Invalid NDJSON or empty input raises ValueError
    with pytest.raises(ValueError):
        json_view.prettify(b'{"a": 1}\n{invalid\n', meta)
    with pytest.raises(ValueError):
        json_view.prettify(b"", meta)
    with pytest.raises(ValueError):
        json_view.prettify(b"   \n  \n", meta)


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
    assert json_view.render_priority(
        b"data", Metadata(content_type="application/x-ndjson")
    )
    assert json_view.render_priority(
        b"data", Metadata(content_type="application/ndjson")
    )
    assert not json_view.render_priority(b"data", Metadata(content_type="text/plain"))
    assert not json_view.render_priority(b"", Metadata(content_type="application/json"))
    assert not json_view.render_priority(b"", Metadata(content_type="application/x-ndjson"))
