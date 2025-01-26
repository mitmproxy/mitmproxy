import re
import sys

import pytest

from mitmproxy import options
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import window
from mitmproxy.tools.console.master import ConsoleMaster
from mitmproxy.utils.signals import _SignalMixin


def tokenize(input: str) -> list[str]:
    keys = []
    for i, k in enumerate(re.split("[<>]", input)):
        if i % 2:
            keys.append(k)
        else:
            keys.extend(k)
    return keys


class ConsoleTestMaster(ConsoleMaster):
    def __init__(self, opts: options.Options) -> None:
        super().__init__(opts)
        self.addons.remove(self.addons.get("tlsconfig"))

    def type(self, input: str) -> None:
        for key in tokenize(input):
            self.window.keypress(self.ui.get_cols_rows(), key)

    def screen_contents(self) -> str:
        return b"\n".join(self.window.render((80, 24), True).text).decode()


@pytest.fixture
def console(monkeypatch) -> ConsoleTestMaster:
    """Stupid workaround for https://youtrack.jetbrains.com/issue/PY-30279/"""


@pytest.fixture
async def console(monkeypatch) -> ConsoleTestMaster:  # noqa
    # monkeypatch.setattr(window.Screen, "get_cols_rows", lambda self: (120, 120))
    monkeypatch.setattr(window.Screen, "start", lambda *_: True)
    monkeypatch.setattr(ConsoleTestMaster, "sig_call_in", lambda *_, **__: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    # extremely hacky: the console UI heavily depends on global signals
    # that are unfortunately shared across tests
    # Here we clear all existing signals so that we don't interact with previous instantiations.
    for sig in signals.__dict__.values():
        if isinstance(sig, _SignalMixin):
            sig.receivers.clear()

    opts = options.Options()
    m = ConsoleTestMaster(opts)
    opts.server = False
    opts.console_mouse = False
    await m.running()
    yield m
    await m.done()
