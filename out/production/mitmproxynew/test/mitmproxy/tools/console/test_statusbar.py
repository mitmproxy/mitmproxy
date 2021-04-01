import pytest

from mitmproxy import options
from mitmproxy.tools.console import statusbar, master


def test_statusbar(monkeypatch):
    o = options.Options()
    m = master.ConsoleMaster(o)
    m.options.update(
        modify_headers=[":~q:foo:bar"],
        modify_body=[":~q:foo:bar"],
        ignore_hosts=["example.com", "example.org"],
        tcp_hosts=["example.tcp"],
        intercept="~q",
        view_filter="~dst example.com",
        stickycookie="~dst example.com",
        stickyauth="~dst example.com",
        console_default_contentview="javascript",
        anticache=True,
        anticomp=True,
        showhost=True,
        server_replay_refresh=False,
        server_replay_kill_extra=True,
        upstream_cert=False,
        stream_large_bodies="3m",
        mode="transparent",
    )

    m.options.update(view_order='url', console_focus_follow=True)
    monkeypatch.setattr(m.addons.get("clientplayback"), "count", lambda: 42)
    monkeypatch.setattr(m.addons.get("serverplayback"), "count", lambda: 42)
    monkeypatch.setattr(statusbar.StatusBar, "refresh", lambda x: None)

    bar = statusbar.StatusBar(m)  # this already causes a redraw
    assert bar.ib._w


@pytest.mark.parametrize("message,ready_message", [
    ("", [(None, ""), ("warn", "")]),
    (("info", "Line fits into statusbar"), [("info", "Line fits into statusbar"),
                                            ("warn", "")]),
    ("Line doesn't fit into statusbar", [(None, "Line doesn'\u2026"),
                                         ("warn", "(more in eventlog)")]),
    (("alert", "Two lines.\nFirst fits"), [("alert", "Two lines."),
                                           ("warn", "(more in eventlog)")]),
    ("Two long lines\nFirst doesn't fit", [(None, "Two long li\u2026"),
                                           ("warn", "(more in eventlog)")])
])
def test_shorten_message(message, ready_message):
    o = options.Options()
    m = master.ConsoleMaster(o)
    ab = statusbar.ActionBar(m)
    assert ab.shorten_message(message, max_width=30) == ready_message


def test_shorten_message_narrow():
    o = options.Options()
    m = master.ConsoleMaster(o)
    ab = statusbar.ActionBar(m)
    shorten_msg = ab.shorten_message("error", max_width=4)
    assert shorten_msg == [(None, "\u2026"), ("warn", "(more in eventlog)")]
