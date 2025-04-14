from .test__api import FailingContentview
from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews import prettify_message
from mitmproxy.contentviews import raw
from mitmproxy.contentviews import registry
from mitmproxy.test import tflow


def test_view_selection():
    assert registry.get_view(b"foo", Metadata(), None).name == "Raw"

    assert (
        registry.get_view(
            b"<html></html>", Metadata(content_type="text/html"), None
        ).name
        == "XML/HTML"
    )

    assert (
        registry.get_view(b"foo", Metadata(content_type="text/flibble"), None).name
        == "Raw"
    )

    assert (
        registry.get_view(
            b"<xml></xml>", Metadata(content_type="text/flibble"), None
        ).name
        == "XML/HTML"
    )

    assert (
        registry.get_view(
            b"<svg></svg>", Metadata(content_type="image/svg+xml"), None
        ).name
        == "XML/HTML"
    )

    assert (
        registry.get_view(
            b"{}", Metadata(content_type="application/acme+json"), None
        ).name
        == "JSON"
    )

    assert (
        registry.get_view(
            b"verybinary", Metadata(content_type="image/new-magic-image-format"), None
        ).name
        == "Image"
    )

    assert registry.get_view(b"\xff" * 30, Metadata(), None).name == "Hex Dump"

    assert registry.get_view(b"", Metadata(), None).name == "Raw"


class TestPrettifyMessage:
    def test_empty_content(self):
        f = tflow.tflow()
        f.request.content = None
        result = prettify_message(f.request, f, None)
        assert result.text == "Content is missing."
        assert result.syntax_highlight == "error"
        assert result.view_name is None

    def test_hex_stream(self):
        f = tflow.tflow()
        f.request.content = b"content"
        result = prettify_message(f.request, f, "hex stream")
        assert result.text == "636f6e74656e74"  # hex representation of "content"
        assert result.syntax_highlight == "none"
        assert result.view_name == "Hex Stream"

    def test_view_failure_auto(self):
        f = tflow.tflow()
        f.request.content = b"content"

        failing_view = FailingContentview()
        registry.register(failing_view)
        registry.register(raw)

        result = prettify_message(f.request, f, None)
        assert result.text == "content"
        assert result.syntax_highlight == "none"
        assert result.view_name == "Raw"
        assert "[failed to parse as Failing]" in result.description

    def test_view_failure_explicit(self):
        f = tflow.tflow()
        f.request.content = b"content"

        failing_view = FailingContentview()
        registry.register(failing_view)

        result = prettify_message(f.request, f, "failing")
        assert "Couldn't parse as Failing" in result.text
        assert result.syntax_highlight == "error"
        assert result.view_name == "Failing"
