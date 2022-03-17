import asyncio
import re
import sys
from typing import List

import pytest

import mitmproxy.options
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

    def screen_contents(self) -> str:
        return b"\n".join(self.window.render((80, 24), True)._text_content()).decode()


@pytest.fixture
def console(monkeypatch) -> ConsoleTestMaster:
    # monkeypatch.setattr(window.Screen, "get_cols_rows", lambda self: (120, 120))
    monkeypatch.setattr(window.Screen, "start", lambda *_: True)
    monkeypatch.setattr(ConsoleTestMaster, "sig_call_in", lambda *_, **__: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)

    async def make_master():
        opts = mitmproxy.options.Options()
        m = ConsoleTestMaster(opts)
        opts.server = False
        await m.running()
        return m
    return asyncio.run(make_master())


def test_integration(tdata, console):
    console.type(f":view.flows.load {tdata.path('mitmproxy/data/dumpfile-7.mitm')}<enter>")
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
