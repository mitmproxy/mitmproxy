from unittest.mock import Mock


def test_spawn_editor(monkeypatch, console):
    text_data = "text"
    binary_data = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"

    console.get_editor = Mock()
    console.get_editor.return_value = "editor"
    console.get_hex_editor = Mock()
    console.get_hex_editor.return_value = "editor"
    monkeypatch.setattr("subprocess.call", (lambda _: None))

    console.loop = Mock()
    console.loop.stop = Mock()
    console.loop.start = Mock()
    console.loop.draw_screen = Mock()

    console.spawn_editor(text_data)
    console.get_editor.assert_called_once()

    console.spawn_editor(binary_data)
    console.get_hex_editor.assert_called_once()


def test_get_hex_editor(monkeypatch, console):
    test_editor = "hexedit"
    monkeypatch.setattr("shutil.which", lambda x: x == test_editor)
    editor = console.get_hex_editor()
    assert editor == test_editor
