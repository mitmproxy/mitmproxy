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
        assert len((km.list("commands"))) == 1

        km.handle("unknown", "unknown")
        assert not km.executor.called

        km.handle("options", "key")
        assert km.executor.called

        km.add("glob", "str", ["global"])
        km.executor = mock.Mock()
        km.handle("options", "glob")
        assert km.executor.called

        assert len((km.list("global"))) == 1


def test_join():
    with taddons.context() as tctx:
        km = keymap.Keymap(tctx.master)
        km.add("key", "str", ["options"], "help1")
        km.add("key", "str", ["commands"])
        return
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
