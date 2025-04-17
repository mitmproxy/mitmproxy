from .test__api import FailingPrettifyContentview
from mitmproxy.contentviews import ContentviewRegistry
from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews import prettify_message
from mitmproxy.contentviews import raw
from mitmproxy.contentviews import registry
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_view_selection():
    assert registry.get_view(b"foo", Metadata()).name == "Raw"

    assert (
        registry.get_view(b"<html></html>", Metadata(content_type="text/html")).name
        == "XML/HTML"
    )

    assert (
        registry.get_view(b"foo", Metadata(content_type="text/flibble")).name == "Raw"
    )

    assert (
        registry.get_view(b"<xml></xml>", Metadata(content_type="text/flibble")).name
        == "XML/HTML"
    )

    assert (
        registry.get_view(b"<svg></svg>", Metadata(content_type="image/svg+xml")).name
        == "XML/HTML"
    )

    assert (
        registry.get_view(b"{}", Metadata(content_type="application/acme+json")).name
        == "JSON"
    )

    assert (
        registry.get_view(
            b"verybinary", Metadata(content_type="image/new-magic-image-format")
        ).name
        == "Image"
    )

    assert registry.get_view(b"\xff" * 30, Metadata()).name == "Hex Dump"

    assert registry.get_view(b"", Metadata()).name == "Raw"


class TestPrettifyMessage:
    def test_empty_content(self):
        with taddons.context():
            f = tflow.tflow()
            f.request.content = None
            result = prettify_message(f.request, f)
            assert result.text == "Content is missing."
            assert result.syntax_highlight == "error"
            assert result.view_name is None

    def test_hex_stream(self):
        with taddons.context():
            f = tflow.tflow()
            f.request.content = b"content"
            result = prettify_message(f.request, f, "hex stream")
            assert result.text == "636f6e74656e74"  # hex representation of "content"
            assert result.syntax_highlight == "none"
            assert result.view_name == "Hex Stream"

    def test_view_failure_auto(self):
        registry = ContentviewRegistry()
        with taddons.context():
            f = tflow.tflow()
            f.request.content = b"content"

            failing_view = FailingPrettifyContentview()
            registry.register(failing_view)
            registry.register(raw)

            result = prettify_message(f.request, f, registry=registry)
            assert result.text == "content"
            assert result.syntax_highlight == "none"
            assert result.view_name == "Raw"
            assert "[failed to parse as FailingPrettify]" in result.description

    def test_view_failure_explicit(self):
        registry = ContentviewRegistry()
        with taddons.context():
            f = tflow.tflow()
            f.request.content = b"content"

            failing_view = FailingPrettifyContentview()
            registry.register(failing_view)

            result = prettify_message(f.request, f, "failing", registry=registry)
            assert "Couldn't parse as FailingPrettify" in result.text
            assert result.syntax_highlight == "error"
            assert result.view_name == "FailingPrettify"
