import unittest.mock as mock

import pytest

from mitmproxy.tools.console.consoleaddons import ConsoleAddon


class TestConsoleAddonVersionInfo:
    @pytest.fixture
    def master(self):
        master = mock.MagicMock()
        master.switch_view = mock.MagicMock()
        return master

    def test_view_versioninfo_command_exists(self, master):
        addon = ConsoleAddon(master)

        assert hasattr(addon, "view_versioninfo")
        assert callable(addon.view_versioninfo)

    def test_view_versioninfo_calls_switch_view(self, master):
        addon = ConsoleAddon(master)

        addon.view_versioninfo()

        master.switch_view.assert_called_once_with("versioninfo")

    def test_view_versioninfo_docstring(self, master):
        addon = ConsoleAddon(master)

        assert addon.view_versioninfo.__doc__ is not None
        assert "version" in addon.view_versioninfo.__doc__.lower()
