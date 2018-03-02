import pytest

from mitmproxy import options
from mitmproxy.tools.console import statusbar, master
from unittest import mock


def test_statusbar(monkeypatch):
    o = options.Options()
    m = master.ConsoleMaster(o)
    m.options.update(
        setheaders=[":~q:foo:bar"],
        replacements=[":~q:foo:bar"],
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

    bar = statusbar.StatusBar(m)  # this already causes a redraw
    assert bar.ib._w


@pytest.mark.parametrize("message,ready_message", [
    ("", [(None, ""), ("warn", "")]),
    (("info", "Line fits into statusbar"), [("info", "Line fits into statusbar"),
                                            ("warn", "")]),
    ("Line doesn't fit into statusbar", [(None, "Line does..."),
                                         ("warn", "(more in eventlog)")]),
    (("alert", "Two lines.\nFirst fits"), [("alert", "Two lines."),
                                           ("warn", "(more in eventlog)")]),
    ("Two long lines\nFirst doesn't fit", [(None, "Two long ..."),
                                           ("warn", "(more in eventlog)")])
])
def test_prep_message(message, ready_message):
    m = mock.Mock()
    m.ui.get_cols_rows.return_value = (30, 30)
    ab = statusbar.ActionBar(m)
    assert ab.prep_message(message) == ready_message


def test_prep_message_narrow():
    m = mock.Mock()
    m.ui.get_cols_rows.return_value = (4, 4)
    ab = statusbar.ActionBar(m)
    prep_msg = ab.prep_message("error")
    assert prep_msg == [(None, "..."), ("warn", "(more in eventlog)")]
