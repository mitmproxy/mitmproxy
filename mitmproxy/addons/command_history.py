import collections
import os
import typing

from mitmproxy import command
from mitmproxy import ctx


class CommandHistory:
    def __init__(self, size: int = 300) -> None:
        self.saved_commands: typing.Deque[str] = collections.deque(
            maxlen=size
        )
        self.index: int = 0

        self.filter: str = ''
        self.filtered_index: int = 0
        self.filtered_commands: typing.Deque[str] = collections.deque()
        self.filter_active: bool = True

        _command_history_path = os.path.join(os.path.expanduser(ctx.options.confdir), 'command_history')
        _history_lines = []
        if os.path.exists(_command_history_path):
            _history_lines = open(_command_history_path, 'r').readlines()

        self.command_history_file = open(_command_history_path, 'w')

        for l in _history_lines:
            self.add_command(l.strip(), True)

    @property
    def last_index(self):
        return len(self.saved_commands) - 1

    @property
    def last_filtered_index(self):
        return len(self.filtered_commands) - 1

    @command.command("command_history.clear")
    def clear_history(self):
        self.saved_commands.clear()
        self.index = 0
        self.command_history_file.truncate(0)
        self.command_history_file.seek(0)
        self.command_history_file.flush()
        self.filter = ''
        self.filtered_index = 0
        self.filtered_commands.clear()
        self.filter_active = True

    @command.command("command_history.next")
    def get_next(self) -> str:
        if self.last_index == -1:
            return ''

        if self.filter != '':
            if self.filtered_index < self.last_filtered_index:
                self.filtered_index = self.filtered_index + 1
            ret = self.filtered_commands[self.filtered_index]
        else:
            if self.index == -1:
                ret = ''
            elif self.index < self.last_index:
                self.index = self.index + 1
                ret = self.saved_commands[self.index]
            else:
                self.index = -1
                ret = ''

        return ret

    @command.command("command_history.prev")
    def get_prev(self) -> str:
        if self.last_index == -1:
            return ''

        if self.filter != '':
            if self.filtered_index > 0:
                self.filtered_index = self.filtered_index - 1
            ret = self.filtered_commands[self.filtered_index]
        else:
            if self.index == -1:
                self.index = self.last_index
            elif self.index > 0:
                self.index = self.index - 1

            ret = self.saved_commands[self.index]

        return ret

    @command.command("command_history.filter")
    def set_filter(self, command: str) -> None:
        """
        This is used when the user starts typing part of a command
        and then press the "up" arrow. This way, the results returned are
        only for the command that the user started typing
        """
        if command.strip() == '':
            return

        if self.filter != '':
            last_filtered_command = self.filtered_commands[-1]
            if command == last_filtered_command:
                self.filter = ''
                self.filtered_commands = []
                self.filtered_index = 0
        else:
            self.filter = command
            _filtered_commands = [c for c in self.saved_commands if c.startswith(command)]
            self.filtered_commands = collections.deque(_filtered_commands)

            if command not in self.filtered_commands:
                self.filtered_commands.append(command)

            self.filtered_index = self.last_filtered_index

        # No commands found, so act like no filter was added
        if len(self.filtered_commands) == 1:
            self.add_command(command)
            self.filter = ''

    @command.command("command_history.cancel")
    def restart(self) -> None:
        self.index = -1
        self.filter = ''
        self.filtered_commands = []
        self.filtered_index = 0

    @command.command("command_history.add")
    def add_command(self, command: str, execution: bool = False) -> None:
        if command.strip() == '':
            return

        if execution:
            if command in self.saved_commands:
                self.saved_commands.remove(command)

            self.saved_commands.append(command)

            _history_str = "\n".join(self.saved_commands)
            self.command_history_file.truncate(0)
            self.command_history_file.seek(0)
            self.command_history_file.write(_history_str)
            self.command_history_file.flush()

            self.restart()
        else:
            if command not in self.saved_commands:
                self.saved_commands.append(command)
