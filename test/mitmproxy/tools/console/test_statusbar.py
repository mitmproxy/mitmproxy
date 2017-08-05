from mitmproxy import options
from mitmproxy.tools.console import statusbar, master


def test_statusbar(monkeypatch):
    o = options.Options(
        setheaders=[":~q:foo:bar"],
        replacements=[":~q:foo:bar"],
        ignore_hosts=["example.com", "example.org"],
        tcp_hosts=["example.tcp"],
        intercept="~q",
        view_filter="~dst example.com",
        stickycookie="~dst example.com",
        stickyauth="~dst example.com",
        default_contentview="javascript",
        anticache=True,
        anticomp=True,
        showhost=True,
        refresh_server_playback=False,
        replay_kill_extra=True,
        upstream_cert=False,
        stream_large_bodies="3m",
        mode="transparent",
        scripts=["nonexistent"],
        save_stream_file="foo",
    )
    m = master.ConsoleMaster(o)
    m.options.update(view_order='url', console_focus_follow=True)
    monkeypatch.setattr(m.addons.get("clientplayback"), "count", lambda: 42)
    monkeypatch.setattr(m.addons.get("serverplayback"), "count", lambda: 42)

    bar = statusbar.StatusBar(m)  # this already causes a redraw
    assert bar.ib._w
