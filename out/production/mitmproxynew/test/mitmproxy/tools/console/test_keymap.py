from mitmproxy.tools.console import keymap
from mitmproxy.test import taddons
from unittest import mock
import pytest


def test_binding():
    b = keymap.Binding("space", "cmd", ["options"], "")
    assert b.keyspec() == " "


def test_bind():
    with taddons.context() as tctx:
        km = keymap.Keymap(tctx.master)
        km.executor = mock.Mock()

        with pytest.raises(ValueError):
            km.add("foo", "bar", ["unsupported"])

        km.add("key", "str", ["options", "commands"])
        assert km.get("options", "key")
        assert km.get("commands", "key")
        assert not km.get("flowlist", "key")
        assert len(km.list("commands")) == 1

        km.handle("unknown", "unknown")
        assert not km.executor.called

        km.handle("options", "key")
        assert km.executor.called

        km.add("glob", "str", ["global"])
        km.executor = mock.Mock()
        km.handle("options", "glob")
        assert km.executor.called

        assert len(km.list("global")) == 1


def test_join():
    with taddons.context() as tctx:
        km = keymap.Keymap(tctx.master)
        km.add("key", "str", ["options"], "help1")
        km.add("key", "str", ["commands"])

        assert len(km.bindings) == 1
        assert len(km.bindings[0].contexts) == 2
        assert km.bindings[0].help == "help1"
        km.add("key", "str", ["commands"], "help2")
        assert len(km.bindings) == 1
        assert len(km.bindings[0].contexts) == 2
        assert km.bindings[0].help == "help2"

        assert km.get("commands", "key")
        km.unbind(km.bindings[0])
        assert len(km.bindings) == 0
        assert not km.get("commands", "key")


def test_remove():
    with taddons.context() as tctx:
        km = keymap.Keymap(tctx.master)
        km.add("key", "str", ["options", "commands"], "help1")
        assert len(km.bindings) == 1
        assert "options" in km.bindings[0].contexts

        km.remove("key", ["options"])
        assert len(km.bindings) == 1
        assert "options" not in km.bindings[0].contexts

        km.remove("key", ["commands"])
        assert len(km.bindings) == 0


def test_load_path(tmpdir):
    dst = str(tmpdir.join("conf"))

    kmc = keymap.KeymapConfig()
    with taddons.context(kmc) as tctx:
        km = keymap.Keymap(tctx.master)
        tctx.master.keymap = km

        with open(dst, 'wb') as f:
            f.write(b"\xff\xff\xff")
        with pytest.raises(keymap.KeyBindingError, match="expected UTF8"):
            kmc.load_path(km, dst)

        with open(dst, 'w') as f:
            f.write("'''")
        with pytest.raises(keymap.KeyBindingError):
            kmc.load_path(km, dst)

        with open(dst, 'w') as f:
            f.write(
                """
                    -   key: key1
                        ctx: [unknown]
                        cmd: >
                            foo bar
                            foo bar
                """
            )
        with pytest.raises(keymap.KeyBindingError):
            kmc.load_path(km, dst)

        with open(dst, 'w') as f:
            f.write(
                """
                    -   key: key1
                        ctx: [chooser]
                        help: one
                        cmd: >
                            foo bar
                            foo bar
                """
            )
        kmc.load_path(km, dst)
        assert(km.get("chooser", "key1"))

        with open(dst, 'w') as f:
            f.write(
                """
                    -   key: key2
                        ctx: [flowlist]
                        cmd: foo
                    -   key: key2
                        ctx: [flowview]
                        cmd: bar
                """
            )
        kmc.load_path(km, dst)
        assert(km.get("flowlist", "key2"))
        assert(km.get("flowview", "key2"))

        km.add("key123", "str", ["flowlist", "flowview"])
        with open(dst, 'w') as f:
            f.write(
                """
                    -   key: key123
                        ctx: [options]
                        cmd: foo
                """
            )
        kmc.load_path(km, dst)
        assert(km.get("flowlist", "key123"))
        assert(km.get("flowview", "key123"))
        assert(km.get("options", "key123"))


def test_parse():
    kmc = keymap.KeymapConfig()
    with taddons.context(kmc):
        assert kmc.parse("") == []
        assert kmc.parse("\n\n\n   \n") == []
        with pytest.raises(keymap.KeyBindingError, match="expected a list of keys"):
            kmc.parse("key: val")
        with pytest.raises(keymap.KeyBindingError, match="expected a list of keys"):
            kmc.parse("val")
        with pytest.raises(keymap.KeyBindingError, match="Unknown key attributes"):
            kmc.parse(
                """
                    -   key: key1
                        nonexistent: bar
                """
            )
        with pytest.raises(keymap.KeyBindingError, match="Missing required key attributes"):
            kmc.parse(
                """
                    -   help: key1
                """
            )
        with pytest.raises(keymap.KeyBindingError, match="Invalid type for cmd"):
            kmc.parse(
                """
                    -   key: key1
                        cmd: [ cmd ]
                """
            )
        with pytest.raises(keymap.KeyBindingError, match="Invalid type for ctx"):
            kmc.parse(
                """
                    -   key: key1
                        ctx: foo
                        cmd: cmd
                """
            )
        assert kmc.parse(
            """
                -   key: key1
                    ctx: [one, two]
                    help: one
                    cmd: >
                        foo bar
                        foo bar
            """
        ) == [{"key": "key1", "ctx": ["one", "two"], "help": "one", "cmd": "foo bar foo bar\n"}]