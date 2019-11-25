import collections
import os
import typing

from mitmproxy import command
from mitmproxy import ctx


class CommandHistory:
    def __init__(self, size: int = 300) -> None:
        self.saved_commands: typing.Deque[str] = collections.deque(maxlen=size)

        self.filtered_commands: typing.Deque[str] = collections.deque()
        self.current_index: int = -1
        self.filter_str: str = ''

        _command_history_dir = os.path.expanduser(ctx.options.confdir)
        if not os.path.exists(_command_history_dir):
            os.makedirs(_command_history_dir)

        _command_history_path = os.path.join(_command_history_dir, 'command_history')
        _history_lines: typing.List[str] = []
        if os.path.exists(_command_history_path):
            _history_lines = open(_command_history_path, 'r').readlines()

        self.command_history_file = open(_command_history_path, 'w')

        for l in _history_lines:
            self.add_command(l.strip())

    @property
    def last_filtered_index(self):
        return len(self.filtered_commands) - 1

    @command.command("command_history.clear")
    def clear_history(self):
        self.saved_commands.clear()
        self.filtered_commands.clear()
        self.command_history_file.truncate(0)
        self.command_history_file.seek(0)
        self.command_history_file.flush()
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

        if command in self.saved_commands:
            self.saved_commands.remove(command)

        self.saved_commands.append(command)

        _history_str = "\n".join(self.saved_commands)
        self.command_history_file.truncate(0)
        self.command_history_file.seek(0)
        self.command_history_file.write(_history_str)
        self.command_history_file.flush()

        self.restart()
