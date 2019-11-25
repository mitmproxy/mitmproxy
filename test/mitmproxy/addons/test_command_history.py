import os
import pytest

from mitmproxy import options
from mitmproxy.addons import command_history
from mitmproxy.test import taddons


@pytest.fixture(autouse=True)
def tctx(tmpdir):
    # This runs before each test
    dir_name = tmpdir.mkdir('mitmproxy').dirname
    confdir = dir_name

    opts = options.Options()
    opts.set(*[f"confdir={confdir}"])
    tctx = taddons.context(options=opts)
    ch = command_history.CommandHistory()
    tctx.master.addons.add(ch)
    ch.configure([])

    yield tctx

    # This runs after each test
    ch.cleanup()


class TestCommandHistory:
    def test_existing_command_history(self, tctx):
        commands = ['cmd1', 'cmd2', 'cmd3']
        confdir = tctx.options.confdir
        f = open(os.path.join(confdir, 'command_history'), 'w')
        f.write("\n".join(commands))
        f.close()

        history = command_history.CommandHistory()
        history.configure([])

        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3']

        history.cleanup()

    def test_add_command(self, tctx):
        history = command_history.CommandHistory(3)
        history.configure([])

        history.add_command('cmd1')
        history.add_command('cmd2')

        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd1', 'cmd2']

        history.add_command('')
        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd1', 'cmd2']

        # The history size is only 3. So, we forget the first
        # one command, when adding fourth command
        history.add_command('cmd3')
        history.add_command('cmd4')
        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd2', 'cmd3', 'cmd4']

        history.add_command('')
        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd2', 'cmd3', 'cmd4']

        # Commands with the same text are not repeated in the history one by one
        history.add_command('cmd3')
        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd2', 'cmd4', 'cmd3']

        history.add_command('cmd2')
        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd4', 'cmd3', 'cmd2']

        history.cleanup()

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

        saved_commands = [cmd for cmd in history.saved_commands]
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
            saved_commands = [cmd for cmd in i.saved_commands]
            assert saved_commands == []

        instances[0].add_command('cmd1')
        saved_commands = [cmd for cmd in instances[0].saved_commands]
        assert saved_commands == ['cmd1']

        # These instances haven't yet added a new command, so they haven't
        # yet reloaded their commands from the command file.
        # This is expected, because if the user is filtering a command on
        # another window, we don't want to interfere with that
        saved_commands = [cmd for cmd in instances[1].saved_commands]
        assert saved_commands == []
        saved_commands = [cmd for cmd in instances[2].saved_commands]
        assert saved_commands == []

        # Since the second instanced added a new command, its list of
        # saved commands has been updated to have the commands from the
        # first instance + its own commands
        instances[1].add_command('cmd2')
        saved_commands = [cmd for cmd in instances[1].saved_commands]
        assert saved_commands == ['cmd1', 'cmd2']

        saved_commands = [cmd for cmd in instances[0].saved_commands]
        assert saved_commands == ['cmd1']

        # Third instance is still empty as it has not yet ran any command
        saved_commands = [cmd for cmd in instances[2].saved_commands]
        assert saved_commands == []

        instances[2].add_command('cmd3')
        saved_commands = [cmd for cmd in instances[2].saved_commands]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3']

        instances[0].add_command('cmd4')
        saved_commands = [cmd for cmd in instances[0].saved_commands]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4']

        instances.append(command_history.CommandHistory(10))
        instances[3].configure([])
        saved_commands = [cmd for cmd in instances[3].saved_commands]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4']

        instances[0].add_command('cmd_before_close')
        instances.pop(0)

        saved_commands = [cmd for cmd in instances[0].saved_commands]
        assert saved_commands == ['cmd1', 'cmd2']

        instances[0].add_command('new_cmd')
        saved_commands = [cmd for cmd in instances[0].saved_commands]
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
            saved_commands = [cmd for cmd in i.saved_commands]
            assert saved_commands == []

        instances[0].add_command('cmd1')
        instances[0].add_command('cmd2')
        instances[1].add_command('cmd3')
        instances[1].add_command('cmd4')
        instances[1].add_command('cmd5')

        saved_commands = [cmd for cmd in instances[1].saved_commands]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd5']

        instances.pop()
        instances.pop()

        _path = os.path.join(tctx.options.confdir, 'command_history')
        lines = open(_path, 'r').readlines()
        saved_commands = [cmd.strip() for cmd in lines]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3', 'cmd4', 'cmd5']
