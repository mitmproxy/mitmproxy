import atexit
import collections
import os
import typing

from mitmproxy import command
from mitmproxy import ctx


class CommandHistory:
    def __init__(self, size: int = 300) -> None:
        self.saved_commands: typing.Deque[str] = collections.deque(maxlen=size)
        self.is_configured = False

        self.filtered_commands: typing.Deque[str] = collections.deque()
        self.current_index: int = -1
        self.filter_str: str = ''
        self.command_history_path: str = ''

        atexit.register(self.cleanup)

    def cleanup(self):
        self._sync_saved_commands()

    @property
    def last_filtered_index(self):
        return len(self.filtered_commands) - 1

    @command.command("command_history.clear")
    def clear_history(self):
        self.saved_commands.clear()
        self.filtered_commands.clear()

        with open(self.command_history_path, 'w') as f:
            f.truncate(0)
            f.seek(0)
            f.flush()
            f.close()

        self.restart()

    @command.command("command_history.cancel")
    def restart(self) -> None:
        self.filtered_commands = self.saved_commands.copy()
        self.current_index = -1

    @command.command("command_history.next")
    def get_next(self) -> str:

        if self.current_index == -1 or self.current_index == self.last_filtered_index:
            self.current_index = -1
            return ''
        elif self.current_index < self.last_filtered_index:
            self.current_index += 1

        ret = self.filtered_commands[self.current_index]

        return ret

    @command.command("command_history.prev")
    def get_prev(self) -> str:

        if self.current_index == -1:
            if self.last_filtered_index >= 0:
                self.current_index = self.last_filtered_index
            else:
                return ''

        elif self.current_index > 0:
            self.current_index -= 1

        ret = self.filtered_commands[self.current_index]

        return ret

    @command.command("command_history.filter")
    def set_filter(self, command: str) -> None:
        self.filter_str = command

        _filtered_commands = [c for c in self.saved_commands if c.startswith(command)]
        self.filtered_commands = collections.deque(_filtered_commands)

        if command and command not in self.filtered_commands:
            self.filtered_commands.append(command)

        self.current_index = -1

    @command.command("command_history.add")
    def add_command(self, command: str) -> None:
        if command.strip() == '':
            return

        self._sync_saved_commands()

        if command in self.saved_commands:
            self.saved_commands.remove(command)
        self.saved_commands.append(command)

        _history_str = "\n".join(self.saved_commands)
        with open(self.command_history_path, 'w') as f:
            f.truncate(0)
            f.seek(0)
            f.write(_history_str)
            f.flush()
            f.close()

        self.restart()

    def _sync_saved_commands(self):
        # First read all commands from the file to merge anything that may
        # have come from a different instance of the mitmproxy or sister tools
        if not os.path.exists(self.command_history_path):
            return

        with open(self.command_history_path, 'r') as f:
            _history_lines = f.readlines()
            f.close()

        self.saved_commands.clear()
        for l in _history_lines:
            l = l.strip()
            if l in self.saved_commands:
                self.saved_commands.remove(l)
            self.saved_commands.append(l.strip())

    def configure(self, updated: typing.Set[str]):
        if self.is_configured:
            return

        _command_history_dir = os.path.expanduser(ctx.options.confdir)
        if not os.path.exists(_command_history_dir):
            os.makedirs(_command_history_dir)

        self.command_history_path = os.path.join(_command_history_dir, 'command_history')
        _history_lines: typing.List[str] = []
        if os.path.exists(self.command_history_path):
            with open(self.command_history_path, 'r') as f:
                _history_lines = f.readlines()
                f.close()

        for l in _history_lines:
            self.add_command(l.strip())

        self.is_configured = True
