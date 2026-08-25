from unittest import mock

from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._registry import ContentviewRegistry
from test.mitmproxy.contentviews.test__api import ExampleContentview
from test.mitmproxy.contentviews.test__api import FailingRenderPriorityContentview


def test_register_triggers_on_change():
    registry = ContentviewRegistry()
    view = ExampleContentview()
    callback = mock.Mock()
    registry.on_change.connect(callback)

    registry.register(view)

    callback.assert_called_once_with(view)


def test_replace_view_triggers_on_change_and_logs(caplog):
    registry = ContentviewRegistry()
    view1 = ExampleContentview()
    view2 = ExampleContentview()
    callback = mock.Mock()
    registry.on_change.connect(callback)

    registry.register(view1)
    callback.reset_mock()

    with caplog.at_level("INFO"):
        registry.register(view2)

    callback.assert_called_once_with(view2)
    assert "Replacing existing example contentview." in caplog.text


def test_dunder_methods():
    registry = ContentviewRegistry()
    view = ExampleContentview()

    registry.register(view)

    assert list(registry) == ["example"]
    assert registry["example"] == view
    assert registry["EXAMPLE"] == view
    assert len(registry) == 1
    assert registry.available_views() == ["auto", "example"]


def test_get_view_unknown_name(caplog):
    registry = ContentviewRegistry()
    view = ExampleContentview()

    registry.register(view)

    with caplog.at_level("WARNING"):
        result = registry.get_view(b"data", Metadata(), "unknown")

    assert result == view
    assert "Unknown contentview 'unknown', selecting best match instead." in caplog.text


def test_render_priority_error(caplog):
    registry = ContentviewRegistry()
    view = FailingRenderPriorityContentview()
    registry.register(view)
    registry.register(ExampleContentview)

    v = registry.get_view(b"data", Metadata())
    assert v.name == "Example"
    assert "Error in FailingRenderPriority.render_priority" in caplog.text
