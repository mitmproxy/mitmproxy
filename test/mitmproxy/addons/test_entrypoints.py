from unittest import mock

from mitmproxy import addons


class DummyAddon:
    def __init__(self, name="dummy"):
        self.name = name


class DummyAddonNoName:
    pass


class DummyAddonWithArg:
    def __init__(self, required_arg):
        self.required_arg = required_arg


def dummy_factory():
    return DummyAddon("from_factory")


def dummy_factory_multiple():
    return [DummyAddon("from_factory_1"), DummyAddon("from_factory_2")]


def dummy_factory_with_arg(arg):
    return DummyAddon(arg)


def test_entrypoint_addons_empty():
    with mock.patch("importlib.metadata.entry_points", return_value=[]):
        loaded = addons.entrypoint_addons()
        assert loaded == []


def test_entrypoint_addons_class():
    mock_ep = mock.MagicMock()
    mock_ep.name = "my_addon"
    mock_ep.load.return_value = DummyAddon

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert len(loaded) == 1
        assert isinstance(loaded[0], DummyAddon)
        assert loaded[0].name == "dummy"


def test_entrypoint_addons_instance_without_name():
    mock_ep = mock.MagicMock()
    mock_ep.name = "inferred_name"
    mock_ep.load.return_value = DummyAddonNoName()

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert len(loaded) == 1
        assert isinstance(loaded[0], DummyAddonNoName)
        assert loaded[0].name == "inferred_name"


def test_entrypoint_addons_factory_zero_args():
    mock_ep = mock.MagicMock()
    mock_ep.name = "factory_addon"
    mock_ep.load.return_value = dummy_factory

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert len(loaded) == 1
        assert isinstance(loaded[0], DummyAddon)
        assert loaded[0].name == "from_factory"


def test_entrypoint_addons_factory_returning_list():
    mock_ep = mock.MagicMock()
    mock_ep.name = "factory_list"
    mock_ep.load.return_value = dummy_factory_multiple

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert len(loaded) == 2
        assert loaded[0].name == "from_factory_1"
        assert loaded[1].name == "from_factory_2"


def test_entrypoint_addons_callable_with_required_args():
    mock_ep = mock.MagicMock()
    mock_ep.name = "factory_with_args"
    mock_ep.load.return_value = dummy_factory_with_arg

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        # Callable requires args, so it is loaded as the callable itself (which can act as an addon hook / module)
        assert len(loaded) == 1
        assert loaded[0] is dummy_factory_with_arg


def test_entrypoint_addons_error_handling(caplog):
    mock_ep = mock.MagicMock()
    mock_ep.name = "broken_addon"
    mock_ep.value = "some.pkg:broken"
    mock_ep.load.side_effect = RuntimeError("Failed to import")

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert loaded == []
        assert "Failed to load addon from entry point 'broken_addon'" in caplog.text


def test_default_addons_includes_entrypoints():
    mock_ep = mock.MagicMock()
    mock_ep.name = "plugin_addon"
    mock_ep.load.return_value = DummyAddon("plugin_addon")

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.default_addons()
        names = [getattr(a, "name", None) for a in loaded]
        assert "plugin_addon" in names
