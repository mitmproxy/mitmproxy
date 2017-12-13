
from mitmproxy.tools.console.commander import commander


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
        for start, output in tests:
            cb = commander.CommandBuffer()
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
        for start, output in tests:
            cb = commander.CommandBuffer()
            cb.buf, cb.cursor = start[0], start[1]
            cb.insert("x")
            assert cb.buf == output[0]
            assert cb.cursor == output[1]



