from mitmproxy.tools.console import keymap
from mitmproxy.test import taddons
from unittest import mock
import pytest


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

            km.handle("unknown", "unknown")
            assert not km.executor.called

            km.handle("options", "key")
            assert km.executor.called

            km.add("glob", "str", ["global"])
            km.executor = mock.Mock()
            km.handle("options", "glob")
            assert km.executor.called
