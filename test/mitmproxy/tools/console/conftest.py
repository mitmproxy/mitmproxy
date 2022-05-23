import re
import sys

import pytest

from mitmproxy import options
from mitmproxy.tools.console import window
from mitmproxy.tools.console.master import ConsoleMaster


def tokenize(input: str) -> list[str]:
    keys = []
    for i, k in enumerate(re.split("[<>]", input)):
        if i % 2:
            keys.append(k)
        else:
            keys.extend(k)
    return keys


class ConsoleTestMaster(ConsoleMaster):
    def type(self, input: str) -> None:
        for key in tokenize(input):
            self.window.keypress(self.ui.get_cols_rows(), key)

    def screen_contents(self) -> str:
        return b"\n".join(self.window.render((80, 24), True)._text_content()).decode()


@pytest.fixture
def console(monkeypatch) -> ConsoleTestMaster:
    """Stupid workaround for https://youtrack.jetbrains.com/issue/PY-30279/"""


@pytest.fixture
async def console(monkeypatch) -> ConsoleTestMaster:  # noqa
    # monkeypatch.setattr(window.Screen, "get_cols_rows", lambda self: (120, 120))
    monkeypatch.setattr(window.Screen, "start", lambda *_: True)
    monkeypatch.setattr(ConsoleTestMaster, "sig_call_in", lambda *_, **__: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    opts = options.Options()
    m = ConsoleTestMaster(opts)
    opts.server = False
    opts.console_mouse = False
    await m.running()
    return m
