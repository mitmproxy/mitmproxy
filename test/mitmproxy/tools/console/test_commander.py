from mitmproxy import options
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

    def test_get_option_value(self):
        opts = options.Options(view_filter="value")
        with taddons.context(options=opts) as tctx:
            cb = commander.CommandBuffer(tctx.master)
            assert cb.get_option_value("set unknown_option=") == ""
            assert cb.get_option_value("set intercept=") == ""
            assert cb.get_option_value("set view_filter=") == "value"
