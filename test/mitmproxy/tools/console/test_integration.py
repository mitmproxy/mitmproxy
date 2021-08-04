import re
import sys
from typing import List

import pytest

import mitmproxy.options
from mitmproxy import master
from mitmproxy.tools.console import window
from mitmproxy.tools.console.master import ConsoleMaster


def tokenize(input: str) -> List[str]:
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


@pytest.fixture
def console(monkeypatch):
    monkeypatch.setattr(window.Screen, "get_cols_rows", lambda self: (120, 120))
    monkeypatch.setattr(master.Master, "run_loop", lambda *_: True)
    monkeypatch.setattr(ConsoleTestMaster, "sig_call_in", lambda *_, **__: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    opts = mitmproxy.options.Options()
    m = ConsoleTestMaster(opts)
    m.run()
    return m


def test_integration(tdata, console):
    console.type(f":view.flows.load {tdata.path('mitmproxy/data/dumpfile-7.mitm')}<enter>")
    console.type("<enter><tab><tab>")
    console.type("<space><tab><tab>")  # view second flow


def test_options_home_end(console):
    console.type("O<home><end>")


def test_keybindings_home_end(console):
    console.type("K<home><end>")