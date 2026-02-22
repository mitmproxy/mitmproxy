import pytest

from mitmproxy.tools.console import statusbar


async def test_statusbar(console, monkeypatch):
    console.options.update(
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
        server_replay_extra="kill",
        upstream_cert=False,
        stream_large_bodies="3m",
        mode=["transparent"],
    )
    console.options.update(view_order="url", console_focus_follow=True)
    monkeypatch.setattr(console.addons.get("clientplayback"), "count", lambda: 42)
    monkeypatch.setattr(console.addons.get("serverplayback"), "count", lambda: 42)
    monkeypatch.setattr(statusbar.StatusBar, "refresh", lambda x: None)

    bar = statusbar.StatusBar(console)  # this already causes a redraw
    assert bar.ib._w


@pytest.mark.parametrize(
    "message,ready_message",
    [
        ("", [("", ""), ("warn", "")]),
        (
            ("info", "Line fits into statusbar"),
            [("info", "Line fits into statusbar"), ("warn", "")],
        ),
        (
            "Line doesn't fit into statusbar",
            [("", "Line doesn'\u2026"), ("warn", "(more in eventlog)")],
        ),
        (
            ("alert", "Two lines.\nFirst fits"),
            [("alert", "Two lines."), ("warn", "(more in eventlog)")],
        ),
        (
            "Two long lines\nFirst doesn't fit",
            [("", "Two long li\u2026"), ("warn", "(more in eventlog)")],
        ),
    ],
)
def test_shorten_message(message, ready_message):
    assert statusbar.shorten_message(message, max_width=30) == ready_message


def test_shorten_message_narrow():
    shorten_msg = statusbar.shorten_message("error", max_width=4)
    assert shorten_msg == [("", "\u2026"), ("warn", "(more in eventlog)")]


async def test_console_quickhelp_option(console, monkeypatch):
    """Test that console_quickhelp option controls the display of quick help bar."""
    import urwid

    monkeypatch.setattr(statusbar.StatusBar, "refresh", lambda x: None)

    # quickhelp enabled (default)
    console.options.console_quickhelp = True
    bar = statusbar.StatusBar(console)
    assert isinstance(bar.ab._w, urwid.Pile)
    assert len(bar.ab._w.contents) == 2
    assert isinstance(bar.ab.top._w, urwid.Columns)
    assert isinstance(bar.ab.bottom._w, urwid.Columns)

    # quickhelp disabled
    console.options.console_quickhelp = False
    bar2 = statusbar.StatusBar(console)
    assert isinstance(bar2.ab._w, urwid.Pile)
    assert len(bar2.ab._w.contents) == 0


async def test_console_quickhelp_toggle(console, monkeypatch):
    """Test that toggling console_quickhelp option updates the display."""
    import urwid

    monkeypatch.setattr(statusbar.StatusBar, "refresh", lambda x: None)

    bar = statusbar.StatusBar(console)

    # quickhelp enabled (default)
    assert console.options.console_quickhelp is True
    bar.ab.show_quickhelp()
    assert isinstance(bar.ab._w, urwid.Pile)
    assert len(bar.ab._w.contents) == 2
    assert isinstance(bar.ab.top._w, urwid.Columns)
    assert isinstance(bar.ab.bottom._w, urwid.Columns)

    # quickhelp disabled
    console.options.console_quickhelp = False
    bar.ab.show_quickhelp()
    assert isinstance(bar.ab._w, urwid.Pile)
    assert len(bar.ab._w.contents) == 0

    # quickhelp toggling
    console.options.console_quickhelp = True
    bar.ab.show_quickhelp()
    assert isinstance(bar.ab._w, urwid.Pile)
    assert len(bar.ab._w.contents) == 2
    assert isinstance(bar.ab.top._w, urwid.Columns)
    assert isinstance(bar.ab.bottom._w, urwid.Columns)


async def test_console_quickhelp_hotkey(console):
    """Test that the 'H' hotkey toggles the console_quickhelp option."""
    assert console.options.console_quickhelp is True

    console.type("H")
    assert console.options.console_quickhelp is False

    console.type("H")
    assert console.options.console_quickhelp is True


async def test_console_quickhelp_prompts_visible_when_disabled(console, monkeypatch):
    """Test that prompts and messages are visible even when quickhelp is disabled."""
    import urwid

    monkeypatch.setattr(statusbar.StatusBar, "refresh", lambda x: None)

    # Disable quickhelp
    console.options.console_quickhelp = False
    bar = statusbar.StatusBar(console)

    # Initially, Pile should be empty (quickhelp disabled)
    assert isinstance(bar.ab._w, urwid.Pile)
    assert len(bar.ab._w.contents) == 0

    # Show a message - Pile should now contain widgets
    bar.ab.sig_message("Test message", expire=None)
    assert len(bar.ab._w.contents) == 2
    assert isinstance(bar.ab.top._w, urwid.Text)

    # After showing quickhelp again (when message expires), should hide if disabled
    bar.ab.show_quickhelp()
    assert len(bar.ab._w.contents) == 0

    # Show a prompt - Pile should contain widgets
    bar.ab.sig_prompt("Test prompt", None, lambda x: None)
    assert len(bar.ab._w.contents) == 2
    assert isinstance(bar.ab.top._w, urwid.Edit)

    # Dismiss prompt
    bar.ab.prompt_done()
    assert len(bar.ab._w.contents) == 0
