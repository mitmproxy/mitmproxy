from unittest.mock import MagicMock

from mitmproxy.tools.console.commandexecutor import CommandExecutor


class TestCommandExecutor:
    def test_aliases(self):
        """Test that vim-style :q and :q! aliases are expanded."""
        master = MagicMock()
        executor = CommandExecutor(master)

        executor("q")
        master.commands.execute.assert_called_with("console.view.pop")

        master.reset_mock()
        executor("q!")
        master.commands.execute.assert_called_with("console.exit")

    def test_alias_with_whitespace(self):
        """Test that aliases work with surrounding whitespace."""
        master = MagicMock()
        executor = CommandExecutor(master)

        executor("  q  ")
        master.commands.execute.assert_called_with("console.view.pop")

    def test_non_alias_passthrough(self):
        """Test that non-alias commands are passed through unchanged."""
        master = MagicMock()
        executor = CommandExecutor(master)

        executor("console.view.pop")
        master.commands.execute.assert_called_with("console.view.pop")

    def test_empty_command(self):
        """Test that empty commands are not executed."""
        master = MagicMock()
        executor = CommandExecutor(master)

        executor("   ")
        master.commands.execute.assert_not_called()
