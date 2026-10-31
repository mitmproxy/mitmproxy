from unittest import mock

import pytest

from mitmproxy import addons
from mitmproxy.test import taddons


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


def test_entrypoint_addons_builtin_collision(caplog):
    mock_ep = mock.MagicMock()
    mock_ep.name = "core"
    mock_ep.load.return_value = DummyAddon("core")

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert loaded == []
        assert (
            "Entry point 'core' conflicts with existing addon name(s): ['core']"
            in caplog.text
        )

    # Verify default_addons() starts cleanly despite collision
    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        all_addons = addons.default_addons()
        core_addons = [a for a in all_addons if addons._get_name(a) == "core"]
        assert len(core_addons) == 1


def test_entrypoint_addons_sequence_unnamed_children():
    mock_ep = mock.MagicMock()
    mock_ep.name = "multi_ep"
    child1 = DummyAddonNoName()
    child2 = DummyAddonNoName()
    mock_ep.load.return_value = [child1, child2]

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert len(loaded) == 2
        assert loaded[0].name == "multi_ep_0"
        assert loaded[1].name == "multi_ep_1"

    with taddons.context() as tctx:
        tctx.master.addons.add(*loaded)
        assert tctx.master.addons.get("multi_ep_0") is child1
        assert tctx.master.addons.get("multi_ep_1") is child2


def test_entrypoint_addons_sequence_duplicate_names_atomic(caplog):
    mock_ep = mock.MagicMock()
    mock_ep.name = "dup_ep"
    mock_ep.load.return_value = [DummyAddon("dup"), DummyAddon("dup")]

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert loaded == []
        assert (
            "Entry point 'dup_ep' provides multiple addons with duplicate names"
            in caplog.text
        )


def test_entrypoint_addons_factory_raising_typeerror(caplog):
    def bad_factory():
        # Raises TypeError inside the body of a 0-arg function
        return "str" + 123  # type: ignore

    mock_ep = mock.MagicMock()
    mock_ep.name = "bad_factory_ep"
    mock_ep.value = "pkg:bad_factory"
    mock_ep.load.return_value = bad_factory

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert loaded == []
        assert "Failed to load addon from entry point 'bad_factory_ep'" in caplog.text


def test_entrypoint_addons_raising_load_hook(caplog):
    class BrokenLoadAddon:
        def __init__(self):
            self.name = "broken_load_addon"

        def load(self, loader):
            raise RuntimeError("simulated error in load hook")

    addon_instance = BrokenLoadAddon()
    mock_ep = mock.MagicMock()
    mock_ep.name = "broken_load_ep"
    mock_ep.load.return_value = addon_instance

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert len(loaded) == 1
        assert loaded[0] is addon_instance

    # Registration must not abort or crash startup
    with taddons.context() as tctx:
        tctx.master.addons.add(*loaded)
        assert tctx.master.addons.get("broken_load_addon") is addon_instance
        assert (
            "Addon 'broken_load_addon' from entry point 'broken_load_ep' raised an exception in load():"
            in caplog.text
        )


@pytest.mark.parametrize(
    "env_var", ["MITMPROXY_NO_ENTRYPOINTS", "MITMPROXY_NO_PLUGINS"]
)
def test_entrypoint_addons_opt_out(monkeypatch, env_var):
    mock_ep = mock.MagicMock()
    mock_ep.name = "some_addon"
    mock_ep.load.return_value = DummyAddon("some_addon")

    monkeypatch.setenv(env_var, "1")
    with mock.patch(
        "importlib.metadata.entry_points", return_value=[mock_ep]
    ) as mock_meta:
        loaded = addons.entrypoint_addons()
        assert loaded == []
        mock_meta.assert_not_called()

    monkeypatch.setenv(env_var, "0")
    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert len(loaded) == 1


def test_entrypoint_addons_deterministic_ordering():
    ep_z = mock.MagicMock()
    ep_z.name = "z_addon"
    ep_z.load.return_value = DummyAddon("z_addon")

    ep_a = mock.MagicMock()
    ep_a.name = "a_addon"
    ep_a.load.return_value = DummyAddon("a_addon")

    ep_m = mock.MagicMock()
    ep_m.name = "m_addon"
    ep_m.load.return_value = DummyAddon("m_addon")

    # Entry points returned in arbitrary / reversed order
    with mock.patch("importlib.metadata.entry_points", return_value=[ep_z, ep_a, ep_m]):
        loaded = addons.entrypoint_addons()
        assert [a.name for a in loaded] == ["a_addon", "m_addon", "z_addon"]


def test_entrypoint_addons_subaddon_collision(caplog):
    parent = DummyAddon("parent_addon")
    parent.addons = [DummyAddon("core")]  # Subaddon conflicts with builtin 'core'

    mock_ep = mock.MagicMock()
    mock_ep.name = "parent_ep"
    mock_ep.load.return_value = parent

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.entrypoint_addons()
        assert loaded == []
        assert (
            "Entry point 'parent_ep' conflicts with existing addon name(s): ['core']"
            in caplog.text
        )


def test_entrypoint_addons_metadata_query_error(caplog):
    with mock.patch(
        "importlib.metadata.entry_points",
        side_effect=Exception("Metadata error"),
    ):
        loaded = addons.entrypoint_addons()
        assert loaded == []
        assert (
            "Failed to query entry points for group 'mitmproxy.addons'" in caplog.text
        )


def test_default_addons_includes_entrypoints():
    mock_ep = mock.MagicMock()
    mock_ep.name = "plugin_addon"
    mock_ep.load.return_value = DummyAddon("plugin_addon")

    with mock.patch("importlib.metadata.entry_points", return_value=[mock_ep]):
        loaded = addons.default_addons()
        names = [getattr(a, "name", None) for a in loaded]
        assert "plugin_addon" in names
