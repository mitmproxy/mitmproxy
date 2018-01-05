import urwid

from mitmproxy.test import tflow
from mitmproxy.tools.console import common


def test_format_flow():
    f = tflow.tflow(resp=True)
    assert common.format_flow(f, True)
    assert common.format_flow(f, True, hostheader=True)
    assert common.format_flow(f, True, extended=True)


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
