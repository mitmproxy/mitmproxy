import urwid

from mitmproxy.test import tflow
from mitmproxy.tools.console import common


def test_format_flow():
    f = tflow.tflow(resp=True)
    assert common.format_item(f, True)
    assert common.format_item(f, True, hostheader=True)
    assert common.format_item(f, True, extended=True)


def test_format_http2_flow():
    f = tflow.thttp2flow()
    for m in f.messages:
        assert common.format_http2_item(m, True)


def test_format_keyvals():
    assert common.format_keyvals(
        [
            ("aa", "bb"),
            ("cc", "dd"),
            ("ee", None),
        ]
    )
    wrapped = urwid.BoxAdapter(
        urwid.ListBox(
            urwid.SimpleFocusListWalker(
                common.format_keyvals([("foo", "bar")])
            )
        ), 1
    )
    assert wrapped.render((30, ))
    assert common.format_keyvals(
        [
            ("aa", wrapped)
        ]
    )


def test_format_keyvals_with_index():
    assert common.format_keyvals(
        [
            ("0", "aa", "bb"),
            ("2", "cc", "dd"),
            ("4", "ee", None),
        ]
    )
    wrapped = urwid.BoxAdapter(
        urwid.ListBox(
            urwid.SimpleFocusListWalker(
                common.format_keyvals([("10", "foo", "bar")])
            )
        ), 1
    )
    assert wrapped.render((30, ))
    assert common.format_keyvals(
        [
            ("25", "aa", wrapped)
        ]
    )
