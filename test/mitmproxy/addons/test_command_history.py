import os

from mitmproxy.addons import command_history
from mitmproxy.test import taddons


class TestCommandHistory:
    def test_load_from_file(self, tmpdir):
        commands = ['cmd1', 'cmd2', 'cmd3']
        with open(tmpdir.join('command_history'), 'w') as f:
            f.write("\n".join(commands))

        ch = command_history.CommandHistory()
        with taddons.context(ch) as tctx:
            tctx.options.confdir = str(tmpdir)
            assert ch.history == commands

    def test_add_command(self):
        history = command_history.CommandHistory()

        history.add_command('cmd1')
        history.add_command('cmd2')

        assert history.history == ['cmd1', 'cmd2']

        history.add_command('')
        assert history.history == ['cmd1', 'cmd2']

    def test_get_next_and_prev(self, tctx):
        history = command_history.CommandHistory(5)
        history.configure([])

        history.add_command('cmd1')

        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == 'cmd1'
        assert history.get_prev() == 'cmd1'
        assert history.get_prev() == 'cmd1'
        assert history.get_next() == ''
        assert history.get_next() == ''

        history.add_command('cmd2')

        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == 'cmd2'
        assert history.get_prev() == 'cmd1'
        assert history.get_prev() == 'cmd1'
        assert history.get_next() == 'cmd2'
        assert history.get_next() == ''
        assert history.get_next() == ''

        history.add_command('cmd3')

        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == 'cmd3'
        assert history.get_prev() == 'cmd2'
        assert history.get_prev() == 'cmd1'
        assert history.get_prev() == 'cmd1'
        assert history.get_next() == 'cmd2'
        assert history.get_next() == 'cmd3'
        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == 'cmd3'
        assert history.get_prev() == 'cmd2'

        history.add_command('cmd4')

        assert history.get_prev() == 'cmd4'
        assert history.get_prev() == 'cmd3'
        assert history.get_prev() == 'cmd2'
        assert history.get_prev() == 'cmd1'
        assert history.get_prev() == 'cmd1'
        assert history.get_next() == 'cmd2'
        assert history.get_next() == 'cmd3'
        assert history.get_next() == 'cmd4'
        assert history.get_next() == ''
        assert history.get_next() == ''

        history.add_command('cmd5')
        history.add_command('cmd6')

        assert history.get_next() == ''
        assert history.get_prev() == 'cmd6'
        assert history.get_prev() == 'cmd5'
        assert history.get_prev() == 'cmd4'
        assert history.get_next() == 'cmd5'
        assert history.get_prev() == 'cmd4'
        assert history.get_prev() == 'cmd3'
        assert history.get_prev() == 'cmd2'
        assert history.get_next() == 'cmd3'
        assert history.get_prev() == 'cmd2'
        assert history.get_prev() == 'cmd2'
        assert history.get_next() == 'cmd3'
        assert history.get_next() == 'cmd4'
        assert history.get_next() == 'cmd5'
        assert history.get_next() == 'cmd6'
        assert history.get_next() == ''
        assert history.get_next() == ''

        history.cleanup()

    def test_clear(self, tctx):
        history = command_history.CommandHistory(3)
        history.configure([])

        history.add_command('cmd1')
        history.add_command('cmd2')
        history.clear_history()

        saved_commands = [cmd for cmd in history.history]
        assert saved_commands == []

        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == ''
        assert history.get_prev() == ''

        history.cleanup()

    def test_filter(self, tctx):
        history = command_history.CommandHistory(3)
        history.configure([])

        history.add_command('cmd1')
        history.add_command('cmd2')
        history.add_command('abc')
        history.set_filter('c')

        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == 'c'
        assert history.get_prev() == 'cmd2'
        assert history.get_prev() == 'cmd1'
        assert history.get_prev() == 'cmd1'
        assert history.get_next() == 'cmd2'
        assert history.get_next() == 'c'
        assert history.get_next() == ''
        assert history.get_next() == ''

        history.set_filter('')

        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == 'abc'
        assert history.get_prev() == 'cmd2'
        assert history.get_prev() == 'cmd1'
        assert history.get_prev() == 'cmd1'
        assert history.get_next() == 'cmd2'
        assert history.get_next() == 'abc'
        assert history.get_next() == ''
        assert history.get_next() == ''

        history.cleanup()

    def test_multiple_instances(self, tctx):
        instances = [
            command_history.CommandHistory(10),
            command_history.CommandHistory(10),
            command_history.CommandHistory(10)
        ]

        for i in instances:
            i.configure([])
            saved_commands = [cmd for cmd in i.history]
            assert saved_commands == []

        instances[0].add_command('cmd1')
        saved_commands = [cmd for cmd in instances[0].history]
        assert saved_commands == ['cmd1']

        # These instances haven't yet added a new command, so they haven't
        # yet reloaded their commands from the command file.
        # This is expected, because if the user is filtering a command on
        # another window, we don't want to interfere with that
        saved_commands = [cmd for cmd in instances[1].history]
        assert saved_commands == []
        saved_commands = [cmd for cmd in instances[2].history]
        assert saved_commands == []

        # Since the second instanced added a new command, its list of
        # saved commands has been updated to have the commands from the
        # first instance + its own commands
        instances[1].add_command('cmd2')
        saved_commands = [cmd for cmd in instances[1].history]
        assert saved_commands == ['cmd1', 'cmd2']

        saved_commands = [cmd for cmd in instances[0].history]
        assert saved_commands == ['cmd1']

        # Third instance is still empty as it has not yet ran any command
        saved_commands = [cmd for cmd in instances[2].history]
        assert saved_commands == []

        instances[2].add_command('cmd3')
        saved_commands = [cmd for cmd in instances[2].history]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3']

        instances[0].add_command('cmd4')
        saved_commands = [cmd for cmd in instances[0].history]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4']

        instances.append(command_history.CommandHistory(10))
        instances[3].configure([])
        saved_commands = [cmd for cmd in instances[3].history]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4']

        instances[0].add_command('cmd_before_close')
        instances.pop(0)

        saved_commands = [cmd for cmd in instances[0].history]
        assert saved_commands == ['cmd1', 'cmd2']

        instances[0].add_command('new_cmd')
        saved_commands = [cmd for cmd in instances[0].history]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd_before_close', 'new_cmd']

        instances.pop(0)
        instances.pop(0)
        instances.pop(0)

        _path = os.path.join(tctx.options.confdir, 'command_history')
        lines = open(_path, 'r').readlines()
        saved_commands = [cmd.strip() for cmd in lines]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd_before_close', 'new_cmd']

        instances = [
            command_history.CommandHistory(10),
            command_history.CommandHistory(10)
        ]

        for i in instances:
            i.configure([])
            i.clear_history()
            saved_commands = [cmd for cmd in i.history]
            assert saved_commands == []

        instances[0].add_command('cmd1')
        instances[0].add_command('cmd2')
        instances[1].add_command('cmd3')
        instances[1].add_command('cmd4')
        instances[1].add_command('cmd5')

        saved_commands = [cmd for cmd in instances[1].history]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd5']

        instances.pop()
        instances.pop()

        _path = os.path.join(tctx.options.confdir, 'command_history')
        lines = open(_path, 'r').readlines()
        saved_commands = [cmd.strip() for cmd in lines]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd5']
