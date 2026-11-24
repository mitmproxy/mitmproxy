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


def test_versioninfo_view_command(console):
    """Test that the version info view shows version information via command."""
    console.type(":console.view.versioninfo<enter>")
    screen = console.screen_contents()
    assert "Version Info" in screen
    # Should display version information
    assert "Version" in screen


def test_versioninfo_view_keybinding(console):
    """Test that pressing Y opens the version info view."""
    console.type("Y")
    screen = console.screen_contents()
    assert "Version Info" in screen
    assert "Version" in screen
