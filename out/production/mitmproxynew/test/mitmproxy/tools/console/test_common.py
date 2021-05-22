import urwid

from mitmproxy.test import tflow
from mitmproxy.tools.console import common


def test_format_flow():
    flows = [
        tflow.tflow(resp=True),
        tflow.tflow(err=True),
        tflow.ttcpflow(),
        tflow.ttcpflow(err=True),
    ]
    for f in flows:
        for render_mode in common.RenderMode:
            assert common.format_flow(f, render_mode=render_mode)
            assert common.format_flow(f, render_mode=render_mode, hostheader=True, focused=False)


def test_format_keyvals():
    assert common.format_keyvals(
        [
            ("aa", "bb"),
            ("cc", "dd"),
            ("ee", None),
        ]
    )
    wrapped = urwid.Pile(
        urwid.SimpleFocusListWalker(
            common.format_keyvals([("foo", "bar")])
        )
    )
    assert wrapped.render((30,))
    assert common.format_keyvals(
        [
            ("aa", wrapped)
        ]
    )
