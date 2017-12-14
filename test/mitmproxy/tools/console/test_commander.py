from mitmproxy.tools.console.commander import commander
from mitmproxy.test import taddons


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
                cb.buf, cb.cursor = start[0], start[1]
                cb.backspace()
                assert cb.buf == output[0]
                assert cb.cursor == output[1]

    def test_insert(self):
        tests = [
            [("", 0), ("x", 1)],
            [("a", 0), ("xa", 1)],
            [("xa", 2), ("xax", 3)],
        ]
        with taddons.context() as tctx:
            for start, output in tests:
                cb = commander.CommandBuffer(tctx.master)
                cb.buf, cb.cursor = start[0], start[1]
                cb.insert("x")
                assert cb.buf == output[0]
                assert cb.cursor == output[1]

    def test_cycle_completion(self):
        with taddons.context() as tctx:
            cb = commander.CommandBuffer(tctx.master)
            cb.buf = "foo bar"
            cb.cursor = len(cb.buf)
            cb.cycle_completion()
