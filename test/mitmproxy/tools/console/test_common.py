import urwid

from mitmproxy.test import tflow
from mitmproxy.tools.console import common
from mitmproxy.tools.console.common import format_duration


def test_format_flow():
    for f in tflow.tflows():
        for render_mode in common.RenderMode:
            assert common.format_flow(f, render_mode=render_mode)
            assert common.format_flow(
                f, render_mode=render_mode, hostheader=True, focused=False
            )


def test_format_durations():
    assert format_duration(-0.1) == ("-100ms", "gradient_99")
    assert format_duration(0) == ("0ms", "gradient_99")
    assert format_duration(0.1) == ("100ms", "gradient_43")
    assert format_duration(100) == ("100s", "gradient_00")


def test_format_keyvals():
    assert common.format_keyvals(
        [
            ("aa", "bb"),
            ("cc", "dd"),
            ("ee", None),
        ]
    )
    wrapped = urwid.Pile(
        urwid.SimpleFocusListWalker(common.format_keyvals([("foo", "bar")]))
    )
    assert wrapped.render((30,))
    assert common.format_keyvals([("aa", wrapped)])


def test_truncated_text():
    urwid.set_encoding("utf8")
    half_width_text = common.TruncatedText("Half-width", [])
    full_width_text = common.TruncatedText("ＦＵＬＬ－ＷＩＤＴＨ", [])
    assert half_width_text.render((10,))
    assert full_width_text.render((10,))
