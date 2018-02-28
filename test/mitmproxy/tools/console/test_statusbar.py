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


def test_prep_message():
    o = options.Options()
    m = master.ConsoleMaster(o)
    m.ui = mock.MagicMock()
    m.ui.get_cols_rows = mock.MagicMock(return_value=(50, 50))
    ab = statusbar.ActionBar(m)

    prep_msg = ab.prep_message("Error: Fits into statusbar")
    assert prep_msg == [(None, "Error: Fits into statusbar"), ("warn", "")]

    prep_msg = ab.prep_message("Error: Doesn't fit into statusbar"*2)
    assert prep_msg == [(None, "Error: Doesn't fit into statu..."),
                        ("warn", "(more in eventlog)")]

    prep_msg = ab.prep_message("Error: Two lines.\nFirst fits")
    assert prep_msg == [(None, "Error: Two lines."),
                        ("warn", "(more in eventlog)")]

    prep_msg = ab.prep_message("Error: Two lines"*4 + "\nFirst doensn't fit")
    assert prep_msg == [(None, "Error: Two linesError: Two li..."),
                        ("warn", "(more in eventlog)")]
