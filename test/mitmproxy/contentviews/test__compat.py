from unittest import mock

import pytest

from mitmproxy.contentviews import _compat
from mitmproxy.contentviews.base import View

with pytest.deprecated_call():

    class MockView(View):
        def __init__(self, name: str = "mock"):
            self._name = name
            self.syntax_highlight = "python"

        def __call__(self, data, content_type=None, flow=None, http_message=None):
            return "description", [[("text", "content")]]

        @property
        def name(self) -> str:
            return self._name

        def render_priority(
            self, data, content_type=None, flow=None, http_message=None
        ):
            return 1.0


def test_legacy_contentview():
    mock_view = MockView()
    legacy_view = _compat.LegacyContentview(mock_view)

    # Test name property
    assert legacy_view.name == "mock"

    # Test syntax_highlight property
    assert legacy_view.syntax_highlight == "python"

    # Test render_priority
    data = b"test data"
    metadata = _compat.Metadata(content_type="text/plain", flow=None, http_message=None)
    assert legacy_view.render_priority(data, metadata) == 1.0

    # Test prettify
    result = legacy_view.prettify(data, metadata)
    assert result == "content"


def test_get():
    mock_view = MockView()
    # Test with existing view
    with mock.patch("mitmproxy.contentviews.registry", {"mock": mock_view}):
        with pytest.deprecated_call():
            view = _compat.get("mock")
        assert view == mock_view

    # Test with non-existent view
    with mock.patch("mitmproxy.contentviews.registry", {}):
        with pytest.deprecated_call():
            view = _compat.get("nonexistent")
        assert view is None


def test_remove():
    # The remove function is deprecated and does nothing, but we should still test it
    mock_view = MockView()
    with pytest.deprecated_call():
        _compat.remove(mock_view)  # Should not raise any exceptions
