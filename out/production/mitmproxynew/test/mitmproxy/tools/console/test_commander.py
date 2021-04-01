import pytest

from mitmproxy import options
from mitmproxy.addons import command_history
from mitmproxy.test import taddons
from mitmproxy.tools.console.commander import commander


@pytest.fixture(autouse=True)
def commander_tctx(tmpdir):
    # This runs before each test
    dir_name = tmpdir.mkdir('mitmproxy').dirname
    confdir = dir_name

    opts = options.Options()
    opts.set(*[f"confdir={confdir}"])
    commander_tctx = taddons.context(options=opts)
    ch = command_history.CommandHistory()
    commander_tctx.master.addons.add(ch)
    ch.configure('command_history')

    yield commander_tctx

    # This runs after each test
    ch.clear_history()


class TestListCompleter:
    def test_cycle(self):
        tests = [
            [
                "",
                ["a", "b", "c"],
                ["a", "b", "c", "a"],
                ["c", "b", "a", "c"],
                ["a", "c", "a", "c"]
            ],
            [
                "xxx",
                ["a", "b", "c"],
                ["xxx", "xxx", "xxx"],
                ["xxx", "xxx", "xxx"],
                ["xxx", "xxx", "xxx"]
            ],
            [
                "b",
                ["a", "b", "ba", "bb", "c"],
                ["b", "ba", "bb", "b"],
                ["bb", "ba", "b", "bb"],
                ["b", "bb", "b", "bb"]
            ],
        ]
        for start, opts, cycle, cycle_reverse, cycle_mix in tests:
            c = commander.ListCompleter(start, opts)
            for expected in cycle:
                assert c.cycle() == expected
            for expected in cycle_reverse:
                assert c.cycle(False) == expected
            forward = True
            for expected in cycle_mix:
                assert c.cycle(forward) == expected
                forward = not forward


class TestCommandEdit:

    def test_open_command_bar(self, commander_tctx):
        edit = commander.CommandEdit(commander_tctx.master, '')

        try:
            edit.update()
        except IndexError:
            pytest.faied("Unexpected IndexError")

    def test_insert(self, commander_tctx):
        edit = commander.CommandEdit(commander_tctx.master, '')
        edit.keypress(1, 'a')
        assert edit.get_edit_text() == 'a'

        # Don't let users type a space before starting a command
        # as a usability feature
        edit = commander.CommandEdit(commander_tctx.master, '')
        edit.keypress(1, ' ')
        assert edit.get_edit_text() == ''

    def test_backspace(self, commander_tctx):
        edit = commander.CommandEdit(commander_tctx.master, '')

        edit.keypress(1, 'a')
        edit.keypress(1, 'b')
        assert edit.get_edit_text() == 'ab'

        edit.keypress(1, 'backspace')
        assert edit.get_edit_text() == 'a'

    def test_left(self, commander_tctx):
        edit = commander.CommandEdit(commander_tctx.master, '')

        edit.keypress(1, 'a')
        assert edit.cbuf.cursor == 1

        edit.keypress(1, 'left')
        assert edit.cbuf.cursor == 0

        # Do it again to make sure it won't go negative
        edit.keypress(1, 'left')
        assert edit.cbuf.cursor == 0

    def test_right(self, commander_tctx):
        edit = commander.CommandEdit(commander_tctx.master, '')

        edit.keypress(1, 'a')
        assert edit.cbuf.cursor == 1

        # Make sure cursor won't go past the text
        edit.keypress(1, 'right')
        assert edit.cbuf.cursor == 1

        # Make sure cursor goes left and then back right
        edit.keypress(1, 'left')
        assert edit.cbuf.cursor == 0

        edit.keypress(1, 'right')
        assert edit.cbuf.cursor == 1

    def test_up_and_down(self, commander_tctx):
        edit = commander.CommandEdit(commander_tctx.master, '')

        commander_tctx.master.commands.execute('commands.history.clear')
        commander_tctx.master.commands.execute('commands.history.add "cmd1"')

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit = commander.CommandEdit(commander_tctx.master, '')

        commander_tctx.master.commands.execute('commands.history.clear')
        commander_tctx.master.commands.execute('commands.history.add "cmd1"')
        commander_tctx.master.commands.execute('commands.history.add "cmd2"')

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'a')
        edit.keypress(1, 'b')
        edit.keypress(1, 'c')
        assert edit.get_edit_text() == 'abc'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'abc'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'abc'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'abc'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'abc'

        edit = commander.CommandEdit(commander_tctx.master, '')
        commander_tctx.master.commands.execute('commands.history.add "cmd3"')

        edit.keypress(1, 'z')
        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'z'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'z'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'z'

        edit.keypress(1, 'backspace')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'c')
        assert edit.get_edit_text() == 'c'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'backspace')
        assert edit.get_edit_text() == ''

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'up')
        assert edit.get_edit_text() == 'cmd1'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd2'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == 'cmd3'

        edit.keypress(1, 'down')
        assert edit.get_edit_text() == ''


class TestCommandBuffer:

    def test_backspace(self):
        tests = [
            [("", 0), ("", 0)],
            [("1", 0), ("1", 0)],
            [("1", 1), ("", 0)],
            [("123", 3), ("12", 2)],
            [("123", 2), ("13", 1)],
            [("123", 0), ("123", 0)],
        ]
        with taddons.context() as commander_tctx:
            for start, output in tests:
                cb = commander.CommandBuffer(commander_tctx.master)
                cb.text, cb.cursor = start[0], start[1]
                cb.backspace()
                assert cb.text == output[0]
                assert cb.cursor == output[1]

    def test_left(self):
        cursors = [3, 2, 1, 0, 0]
        with taddons.context() as commander_tctx:
            cb = commander.CommandBuffer(commander_tctx.master)
            cb.text, cb.cursor = "abcd", 4
            for c in cursors:
                cb.left()
                assert cb.cursor == c

    def test_right(self):
        cursors = [1, 2, 3, 4, 4]
        with taddons.context() as commander_tctx:
            cb = commander.CommandBuffer(commander_tctx.master)
            cb.text, cb.cursor = "abcd", 0
            for c in cursors:
                cb.right()
                assert cb.cursor == c

    def test_insert(self):
        tests = [
            [("", 0), ("x", 1)],
            [("a", 0), ("xa", 1)],
            [("xa", 2), ("xax", 3)],
        ]
        with taddons.context() as commander_tctx:
            for start, output in tests:
                cb = commander.CommandBuffer(commander_tctx.master)
                cb.text, cb.cursor = start[0], start[1]
                cb.insert("x")
                assert cb.text == output[0]
                assert cb.cursor == output[1]

    def test_cycle_completion(self):
        with taddons.context() as commander_tctx:
            cb = commander.CommandBuffer(commander_tctx.master)
            cb.text = "foo bar"
            cb.cursor = len(cb.text)
            cb.cycle_completion()

            ce = commander.CommandEdit(commander_tctx.master, "se")
            ce.keypress(1, 'tab')
            ce.update()
            ret = ce.cbuf.render()
            assert ret == [
                ('commander_command', 'set'),
                ('text', ' '),
                ('commander_hint', 'option '),
                ('commander_hint', 'value '),
            ]

    def test_render(self):
        with taddons.context() as commander_tctx:
            cb = commander.CommandBuffer(commander_tctx.master)
            cb.text = "foo"
            assert cb.render()

            cb.text = "set view_filter '~bq test'"
            ret = cb.render()
            assert ret == [
                ('commander_command', 'set'),
                ('text', ' '),
                ('text', 'view_filter'),
                ('text', ' '),
                ('text', "'~bq test'"),
            ]

            cb.text = "set"
            ret = cb.render()
            assert ret == [
                ('commander_command', 'set'),
                ('text', ' '),
                ('commander_hint', 'option '),
                ('commander_hint', 'value '),
            ]
