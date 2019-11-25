import os
import pytest
import shutil
import uuid

from mitmproxy import options
from mitmproxy.addons import command_history
from mitmproxy.test import taddons


@pytest.fixture(autouse=True)
def tctx():
    # This runs before each test
    dir_id = str(uuid.uuid4())
    confdir = os.path.expanduser(f"~/.mitmproxy-test-suite-{dir_id}")
    if not os.path.exists(confdir):
        os.makedirs(confdir)

    opts = options.Options()
    opts.set(*[f"confdir={confdir}"])
    tctx = taddons.context(options=opts)
    ch = command_history.CommandHistory()
    tctx.master.addons.add(ch)

    yield tctx

    # This runs after each test
    ch.command_history_file.close()  # Makes windows happy
    shutil.rmtree(confdir)


class TestCommandHistory:
    def test_existing_command_history(self, tctx):
        commands = ['cmd1', 'cmd2', 'cmd3']
        confdir = tctx.options.confdir
        f = open(os.path.join(confdir, 'command_history'), 'w')
        f.write("\n".join(commands))
        f.close()

        history = command_history.CommandHistory()

        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == ['cmd1', 'cmd2', 'cmd3']

        history.command_history_file.close()

    def test_add_command(self, tctx):
        history = command_history.CommandHistory(3)

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

        history.command_history_file.close()

    def test_get_next_and_prev(self, tctx):
        history = command_history.CommandHistory(5)

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

        history.command_history_file.close()

    def test_clear(self, tctx):
        history = command_history.CommandHistory(3)

        history.add_command('cmd1')
        history.add_command('cmd2')
        history.clear_history()

        saved_commands = [cmd for cmd in history.saved_commands]
        assert saved_commands == []

        assert history.get_next() == ''
        assert history.get_next() == ''
        assert history.get_prev() == ''
        assert history.get_prev() == ''

        history.command_history_file.close()

    def test_filter(self, tctx):
        history = command_history.CommandHistory(3)

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

        history.command_history_file.close()
