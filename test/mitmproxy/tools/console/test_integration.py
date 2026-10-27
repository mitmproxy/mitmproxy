import pytest

from mitmproxy.tools.console import overlay


def test_integration(tdata, console):
    console.type(
        f":view.flows.load {tdata.path('mitmproxy/data/dumpfile-7.mitm')}<enter>"
    )
    console.type("<enter><tab><tab>")
    console.type("<space><tab><tab>")  # view second flow
    assert "http://example.com/" in console.screen_contents()


def test_options_home_end(console):
    console.type("O<home><end>")
    assert "Options" in console.screen_contents()


def test_keybindings_home_end(console):
    console.type("K<home><end>")
    assert "Key Binding" in console.screen_contents()


def test_replay_count(console):
    console.type(":replay.server.count<enter>")
    assert "Data viewer" in console.screen_contents()


@pytest.mark.parametrize("exit_key", ["?", "q", "<esc>"])
def test_options_editor_help(console, monkeypatch, exit_key):
    monkeypatch.setattr(console.ui, "get_cols_rows", lambda: (80, 24))
    console.type("O")
    options = console.window.focus_stack().top_window().optionslist
    options.set_focus(options.walker.opts.index("modify_headers"))
    console.type("<enter>")
    editor = console.window.focus_stack().top_widget()
    assert editor.keyctx == "grideditor"
    console.type("?")

    assert console.window.focus_stack().top_widget().keyctx == "help"
    assert "Insert a row before cursor" in console.screen_contents()
    assert console.window.focus_stack().windows["help"].helpctx == "grideditor"

    console.type(exit_key)
    assert console.window.focus_stack().top_widget() is editor
    console.type("q")
    assert console.window.focus_stack().top_widget().keyctx == "options"


@pytest.mark.parametrize("layout", ["single", "vertical", "horizontal"])
@pytest.mark.parametrize("view_key", ["?", "E", "K", "C"])
def test_options_editor_preserved(console, monkeypatch, layout, view_key):
    monkeypatch.setattr(console.ui, "get_cols_rows", lambda: (80, 24))
    console.options.console_layout = layout
    console.type("O")
    console.overlay(overlay.OptionsOverlay(console, "allow_hosts", [], 5))
    editor = console.window.focus_stack().top_widget()
    console.type("a<enter>example.com<esc>")
    console.type(view_key)

    assert console.window.focus_stack().top_widget() is not editor
    assert console.options.allow_hosts == []
    console.type("q")
    assert console.window.focus_stack().top_widget() is editor
    assert editor.key_responder().walker.get_current_value() == "example.com"

    console.type("q")
    assert console.options.allow_hosts == ["example.com"]


def test_flow_editor_help(console, tdata):
    console.type(
        f":view.flows.load {tdata.path('mitmproxy/data/dumpfile-7.mitm')}<enter>"
    )
    console.switch_view("edit_focus_request_headers")
    editor = console.window.focus_stack().top_widget()
    console.type("?")
    assert console.window.focus_stack().top_window().helpctx == "grideditor"
    console.type("q")
    assert console.window.focus_stack().top_widget() is editor
