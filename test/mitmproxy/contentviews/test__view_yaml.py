import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_yaml import yaml


def test_view_yaml():
    meta = Metadata()
    assert yaml.syntax_highlight == "yaml"
    assert yaml.name == "YAML"

    # Valid single document
    res = yaml.prettify(b"foo: bar\nnum: 42\n", meta)
    assert "foo: bar" in res
    assert "num: 42" in res

    # Valid multi-document
    multi = yaml.prettify(b"doc1: first\n---\ndoc2: second\n", meta)
    assert "doc1: first" in multi
    assert "---" in multi
    assert "doc2: second" in multi

    # Empty and whitespace
    assert yaml.prettify(b"", meta) == ""
    assert yaml.prettify(b"   \n  ", meta) == ""

    # Comment only
    assert yaml.prettify(b"# only a comment\n", meta) == ""

    # Invalid YAML raises ValueError
    with pytest.raises(ValueError, match="Invalid YAML"):
        yaml.prettify(b"foo: [unclosed list", meta)


def test_render_priority():
    assert yaml.render_priority(b"data", Metadata(content_type="application/yaml")) == 1
    assert (
        yaml.render_priority(b"data", Metadata(content_type="application/x-yaml")) == 1
    )
    assert yaml.render_priority(b"data", Metadata(content_type="text/yaml")) == 1
    assert yaml.render_priority(b"data", Metadata(content_type="text/x-yaml")) == 1
    assert yaml.render_priority(b"data", Metadata(content_type="text/x-yml")) == 1
    assert (
        yaml.render_priority(b"data", Metadata(content_type="application/x-yml")) == 1
    )
    assert (
        yaml.render_priority(b"data", Metadata(content_type="application/vnd.api+yaml"))
        == 1
    )
    assert (
        yaml.render_priority(b"data", Metadata(content_type="text/vnd.spec+yaml")) == 1
    )
    assert yaml.render_priority(b"data", Metadata(content_type="application/json")) == 0
    assert yaml.render_priority(b"data", Metadata(content_type="text/plain")) == 0
    assert yaml.render_priority(b"", Metadata(content_type="application/yaml")) == 0
    assert yaml.render_priority(b"data", Metadata(content_type="text/x-yml")) == 1
    assert (
        yaml.render_priority(b"data", Metadata(content_type="application/x-yml")) == 1
    )
