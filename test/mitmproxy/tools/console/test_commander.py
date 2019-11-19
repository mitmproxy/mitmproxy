from mitmproxy.tools.console.commander import commander
from mitmproxy.test import taddons
import pytest


class TestListCompleter:
    def test_cycle(self):
        tests = [
            [
                "",
                ["a", "b", "c"],
                ["a", "b", "c", "a"]
            ],
            [
                "xxx",
                ["a", "b", "c"],
                ["xxx", "xxx", "xxx"]
            ],
            [
                "b",
                ["a", "b", "ba", "bb", "c"],
                ["b", "ba", "bb", "b"]
            ],
        ]
        for start, options, cycle in tests:
            c = commander.ListCompleter(start, options)
            for expected in cycle:
                assert c.cycle() == expected


class TestCommandEdit:
    def test_open_command_bar(self):
        with taddons.context() as tctx:
            history = commander.CommandHistory(tctx.master, size=3)
            edit = commander.CommandEdit(tctx.master, '', history)

            try:
                edit.update()
            except IndexError:
                pytest.faied("Unexpected IndexError")

    def test_insert(self):
        with taddons.context() as tctx:
            history = commander.CommandHistory(tctx.master, size=3)
            edit = commander.CommandEdit(tctx.master, '', history)
            edit.keypress(1, 'a')
            assert edit.get_edit_text() == 'a'

            # Don't let users type a space before starting a command
            # as a usability feature
            history = commander.CommandHistory(tctx.master, size=3)
            edit = commander.CommandEdit(tctx.master, '', history)
            edit.keypress(1, ' ')
            assert edit.get_edit_text() == ''

    def test_backspace(self):
        with taddons.context() as tctx:
            history = commander.CommandHistory(tctx.master, size=3)
            edit = commander.CommandEdit(tctx.master, '', history)
            edit.keypress(1, 'a')
            edit.keypress(1, 'b')
            assert edit.get_edit_text() == 'ab'
            edit.keypress(1, 'backspace')
            assert edit.get_edit_text() == 'a'

    def test_left(self):
        with taddons.context() as tctx:
            history = commander.CommandHistory(tctx.master, size=3)
            edit = commander.CommandEdit(tctx.master, '', history)
            edit.keypress(1, 'a')
            assert edit.cbuf.cursor == 1
            edit.keypress(1, 'left')
            assert edit.cbuf.cursor == 0

            # Do it again to make sure it won't go negative
            edit.keypress(1, 'left')
            assert edit.cbuf.cursor == 0

    def test_right(self):
        with taddons.context() as tctx:
            history = commander.CommandHistory(tctx.master, size=3)
            edit = commander.CommandEdit(tctx.master, '', history)
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

    def test_up_and_down(self):
        with taddons.context() as tctx:
            history = commander.CommandHistory(tctx.master, size=3)
            edit = commander.CommandEdit(tctx.master, '', history)

            buf = commander.CommandBuffer(tctx.master, 'cmd1')
            history.add_command(buf)
            buf = commander.CommandBuffer(tctx.master, 'cmd2')
            history.add_command(buf)

            edit.keypress(1, 'up')
            assert edit.get_edit_text() == 'cmd2'
            edit.keypress(1, 'up')
            assert edit.get_edit_text() == 'cmd1'
            edit.keypress(1, 'up')
            assert edit.get_edit_text() == 'cmd1'

            history = commander.CommandHistory(tctx.master, size=5)
            edit = commander.CommandEdit(tctx.master, '', history)
            edit.keypress(1, 'a')
            edit.keypress(1, 'b')
            edit.keypress(1, 'c')
            assert edit.get_edit_text() == 'abc'
            edit.keypress(1, 'up')
            assert edit.get_edit_text() == ''
            edit.keypress(1, 'down')
            assert edit.get_edit_text() == 'abc'
            edit.keypress(1, 'down')
            assert edit.get_edit_text() == 'abc'

            history = commander.CommandHistory(tctx.master, size=5)
            edit = commander.CommandEdit(tctx.master, '', history)
            buf = commander.CommandBuffer(tctx.master, 'cmd3')
            history.add_command(buf)
            edit.keypress(1, 'z')
            edit.keypress(1, 'up')
            assert edit.get_edit_text() == 'cmd3'
            edit.keypress(1, 'down')
            assert edit.get_edit_text() == 'z'


class TestCommandHistory:
    def fill_history(self, commands):
        with taddons.context() as tctx:
            history = commander.CommandHistory(tctx.master, size=3)
            for c in commands:
                cbuf = commander.CommandBuffer(tctx.master, c)
                history.add_command(cbuf)
        return history, tctx.master

    def test_add_command(self):
        commands = ["command1", "command2"]
        history, tctx_master = self.fill_history(commands)

        saved_commands = [buf.text for buf in history.saved_commands]
        assert saved_commands == [""] + commands

        # The history size is only 3. So, we forget the first
        # one command, when adding fourth command
        cbuf = commander.CommandBuffer(tctx_master, "command3")
        history.add_command(cbuf)
        saved_commands = [buf.text for buf in history.saved_commands]
        assert saved_commands == commands + ["command3"]

        # Commands with the same text are not repeated in the history one by one
        history.add_command(cbuf)
        saved_commands = [buf.text for buf in history.saved_commands]
        assert saved_commands == commands + ["command3"]

        # adding command in execution mode sets index at the beginning of the history
        # and replace the last command buffer if it is empty or has the same text
        cbuf = commander.CommandBuffer(tctx_master, "")
        history.add_command(cbuf)
        history.index = 0
        cbuf = commander.CommandBuffer(tctx_master, "command4")
        history.add_command(cbuf, True)
        assert history.index == history.last_index
        saved_commands = [buf.text for buf in history.saved_commands]
        assert saved_commands == ["command2", "command3", "command4"]

    def test_get_next(self):
        commands = ["command1", "command2"]
        history, tctx_master = self.fill_history(commands)

        history.index = -1
        expected_items = ["", "command1", "command2"]
        for i in range(3):
            assert history.get_next().text == expected_items[i]
        # We are at the last item of the history
        assert history.get_next() is None

    def test_get_prev(self):
        commands = ["command1", "command2"]
        history, tctx_master = self.fill_history(commands)

        expected_items = ["command2", "command1", ""]
        history.index = history.last_index + 1
        for i in range(3):
            assert history.get_prev().text == expected_items[i]
        # We are at the first item of the history
        assert history.get_prev() is None


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
        with taddons.context() as tctx:
            for start, output in tests:
                cb = commander.CommandBuffer(tctx.master)
                cb.text, cb.cursor = start[0], start[1]
                cb.backspace()
                assert cb.text == output[0]
                assert cb.cursor == output[1]

    def test_left(self):
        cursors = [3, 2, 1, 0, 0]
        with taddons.context() as tctx:
            cb = commander.CommandBuffer(tctx.master)
            cb.text, cb.cursor = "abcd", 4
            for c in cursors:
                cb.left()
                assert cb.cursor == c

    def test_right(self):
        cursors = [1, 2, 3, 4, 4]
        with taddons.context() as tctx:
            cb = commander.CommandBuffer(tctx.master)
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
        with taddons.context() as tctx:
            for start, output in tests:
                cb = commander.CommandBuffer(tctx.master)
                cb.text, cb.cursor = start[0], start[1]
                cb.insert("x")
                assert cb.text == output[0]
                assert cb.cursor == output[1]

    def test_cycle_completion(self):
        with taddons.context() as tctx:
            cb = commander.CommandBuffer(tctx.master)
            cb.text = "foo bar"
            cb.cursor = len(cb.text)
            cb.cycle_completion()

            ch = commander.CommandHistory(tctx.master, 30)
            ce = commander.CommandEdit(tctx.master, "se", ch)
            ce.keypress(1, 'tab')
            ce.update()
            ret = ce.cbuf.render()
            assert ret[0] == ('commander_command', 'set')
            assert ret[1] == ('text', ' ')
            assert ret[2] == ('commander_hint', '*options ')

    def test_render(self):
        with taddons.context() as tctx:
            cb = commander.CommandBuffer(tctx.master)
            cb.text = "foo"
            assert cb.render()

            cb.text = 'set view_filter ~bq test'
            ret = cb.render()
            assert ret[0] == ('commander_command', 'set')
            assert ret[1] == ('text', ' ')
            assert ret[2] == ('text', 'view_filter=~bq')
            assert ret[3] == ('text', ' ')
            assert ret[4] == ('text', 'test')

            cb.text = "set"
            ret = cb.render()
            assert ret[0] == ('commander_command', 'set')
            assert ret[1] == ('text', ' ')
            assert ret[2] == ('commander_hint', '*options ')
