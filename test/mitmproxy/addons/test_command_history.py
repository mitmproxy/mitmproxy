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

    def test_get_next_and_prev(self, tmpdir):
        ch = command_history.CommandHistory()

        with taddons.context(ch) as tctx:
            tctx.options.confdir = str(tmpdir)

            ch.add_command('cmd1')

            assert ch.get_next() == ''
            assert ch.get_next() == ''
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_next() == ''
            assert ch.get_next() == ''

            ch.add_command('cmd2')

            assert ch.get_next() == ''
            assert ch.get_next() == ''
            assert ch.get_prev() == 'cmd2'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_next() == 'cmd2'
            assert ch.get_next() == ''
            assert ch.get_next() == ''

            ch.add_command('cmd3')

            assert ch.get_next() == ''
            assert ch.get_next() == ''
            assert ch.get_prev() == 'cmd3'
            assert ch.get_prev() == 'cmd2'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_next() == 'cmd2'
            assert ch.get_next() == 'cmd3'
            assert ch.get_next() == ''
            assert ch.get_next() == ''
            assert ch.get_prev() == 'cmd3'
            assert ch.get_prev() == 'cmd2'

            ch.add_command('cmd4')

            assert ch.get_prev() == 'cmd4'
            assert ch.get_prev() == 'cmd3'
            assert ch.get_prev() == 'cmd2'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_next() == 'cmd2'
            assert ch.get_next() == 'cmd3'
            assert ch.get_next() == 'cmd4'
            assert ch.get_next() == ''
            assert ch.get_next() == ''

            ch.add_command('cmd5')
            ch.add_command('cmd6')

            assert ch.get_next() == ''
            assert ch.get_prev() == 'cmd6'
            assert ch.get_prev() == 'cmd5'
            assert ch.get_prev() == 'cmd4'
            assert ch.get_next() == 'cmd5'
            assert ch.get_prev() == 'cmd4'
            assert ch.get_prev() == 'cmd3'
            assert ch.get_prev() == 'cmd2'
            assert ch.get_next() == 'cmd3'
            assert ch.get_prev() == 'cmd2'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_next() == 'cmd2'
            assert ch.get_next() == 'cmd3'
            assert ch.get_next() == 'cmd4'
            assert ch.get_next() == 'cmd5'
            assert ch.get_next() == 'cmd6'
            assert ch.get_next() == ''
            assert ch.get_next() == ''

            ch.clear_history()

    def test_clear(self, tmpdir):
        ch = command_history.CommandHistory()

        with taddons.context(ch) as tctx:
            tctx.options.confdir = str(tmpdir)
            ch.add_command('cmd1')
            ch.add_command('cmd2')
            ch.clear_history()

            saved_commands = ch.get_history()
            assert saved_commands == []

            assert ch.get_next() == ''
            assert ch.get_next() == ''
            assert ch.get_prev() == ''
            assert ch.get_prev() == ''

            ch.clear_history()

    def test_filter(self, tmpdir):
        ch = command_history.CommandHistory()

        with taddons.context(ch) as tctx:
            tctx.options.confdir = str(tmpdir)

            ch.add_command('cmd1')
            ch.add_command('cmd2')
            ch.add_command('abc')
            ch.set_filter('c')

            assert ch.get_next() == 'c'
            assert ch.get_next() == 'c'
            assert ch.get_prev() == 'cmd2'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_next() == 'cmd2'
            assert ch.get_next() == 'c'
            assert ch.get_next() == 'c'

            ch.set_filter('')

            assert ch.get_next() == ''
            assert ch.get_next() == ''
            assert ch.get_prev() == 'abc'
            assert ch.get_prev() == 'cmd2'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_prev() == 'cmd1'
            assert ch.get_next() == 'cmd2'
            assert ch.get_next() == 'abc'
            assert ch.get_next() == ''
            assert ch.get_next() == ''

            ch.clear_history()

    def test_multiple_instances(self, tmpdir):
        ch = command_history.CommandHistory()
        with taddons.context(ch) as tctx:
            tctx.options.confdir = str(tmpdir)

        instances = [
            command_history.CommandHistory(),
            command_history.CommandHistory(),
            command_history.CommandHistory()
        ]

        for i in instances:
            i.configure('command_history')
            saved_commands = i.get_history()
            assert saved_commands == []

        instances[0].add_command('cmd1')
        saved_commands = instances[0].get_history()
        assert saved_commands == ['cmd1']

        # These instances haven't yet added a new command, so they haven't
        # yet reloaded their commands from the command file.
        # This is expected, because if the user is filtering a command on
        # another window, we don't want to interfere with that
        saved_commands = instances[1].get_history()
        assert saved_commands == []
        saved_commands = instances[2].get_history()
        assert saved_commands == []

        # Since the second instanced added a new command, its list of
        # saved commands has been updated to have the commands from the
        # first instance + its own commands
        instances[1].add_command('cmd2')
        saved_commands = instances[1].get_history()
        assert saved_commands == ['cmd2']

        saved_commands = instances[0].get_history()
        assert saved_commands == ['cmd1']

        # Third instance is still empty as it has not yet ran any command
        saved_commands = instances[2].get_history()
        assert saved_commands == []

        instances[2].add_command('cmd3')
        saved_commands = instances[2].get_history()
        assert saved_commands == ['cmd3']

        instances[0].add_command('cmd4')
        saved_commands = instances[0].get_history()
        assert saved_commands == ['cmd1', 'cmd4']

        instances.append(command_history.CommandHistory())
        instances[3].configure('command_history')
        saved_commands = instances[3].get_history()
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4']

        instances[0].add_command('cmd_before_close')
        instances.pop(0).done()

        saved_commands = instances[0].get_history()
        assert saved_commands == ['cmd2']

        instances[0].add_command('new_cmd')
        saved_commands = instances[0].get_history()
        assert saved_commands == ['cmd2', 'new_cmd']

        instances.pop(0).done()
        instances.pop(0).done()
        instances.pop(0).done()

        _path = os.path.join(tctx.options.confdir, 'command_history')
        lines = open(_path, 'r').readlines()
        saved_commands = [cmd.strip() for cmd in lines]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd_before_close', 'new_cmd']

        instances = [
            command_history.CommandHistory(),
            command_history.CommandHistory()
        ]

        for i in instances:
            i.configure('command_history')
            i.clear_history()
            saved_commands = i.get_history()
            assert saved_commands == []

        instances[0].add_command('cmd1')
        instances[0].add_command('cmd2')
        instances[1].add_command('cmd3')
        instances[1].add_command('cmd4')
        instances[1].add_command('cmd5')

        saved_commands = instances[1].get_history()
        assert saved_commands == ['cmd3', 'cmd4', 'cmd5']

        instances.pop().done()
        instances.pop().done()

        _path = os.path.join(tctx.options.confdir, 'command_history')
        lines = open(_path, 'r').readlines()
        saved_commands = [cmd.strip() for cmd in lines]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd5']
