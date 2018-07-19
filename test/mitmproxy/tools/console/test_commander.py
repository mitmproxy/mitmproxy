
from mitmproxy.tools.console.commander import commander
from mitmproxy.test import taddons


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

    def test_render(self):
        with taddons.context() as tctx:
            cb = commander.CommandBuffer(tctx.master)
            cb.text = "foo"
            assert cb.render()

    def test_flatten(self):
        with taddons.context() as tctx:
            cb = commander.CommandBuffer(tctx.master)
            assert cb.flatten("foo  bar") == "foo bar"
