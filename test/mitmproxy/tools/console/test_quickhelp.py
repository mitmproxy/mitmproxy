import pytest

from mitmproxy.test.tflow import tflow
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import quickhelp
from mitmproxy.tools.console.eventlog import EventLog
from mitmproxy.tools.console.flowlist import FlowListBox
from mitmproxy.tools.console.flowview import FlowView
from mitmproxy.tools.console.grideditor import PathEditor
from mitmproxy.tools.console.help import HelpView
from mitmproxy.tools.console.keybindings import KeyBindings
from mitmproxy.tools.console.keymap import Keymap
from mitmproxy.tools.console.options import Options
from mitmproxy.tools.console.overlay import SimpleOverlay


@pytest.fixture(scope="module")
def keymap() -> Keymap:
    km = Keymap(None)
    defaultkeys.map(km)
    return km


tflow2 = tflow()
tflow2.intercept()
tflow2.backup()
tflow2.marked = "x"


@pytest.mark.parametrize(
    "widget, flow, is_root_widget",
    [
        (FlowListBox, None, False),
        (FlowListBox, tflow(), False),
        (FlowView, tflow2, True),
        (KeyBindings, None, True),
        (Options, None, True),
        (HelpView, None, False),
        (EventLog, None, True),
        (PathEditor, None, False),
        (SimpleOverlay, None, False),
    ],
)
def test_quickhelp(widget, flow, keymap, is_root_widget):
    qh = quickhelp.make(widget, flow, is_root_widget)
    for row in [qh.top_items, qh.bottom_items]:
        for title, v in row.items():
            if isinstance(v, quickhelp.BasicKeyHelp):
                key_short = v.key
            else:
                b = keymap.binding_for_help(v)
                if b is None:
                    raise AssertionError(f"No binding found for help text: {v}")
                key_short = b.key_short()
            assert len(key_short) + len(title) < 14


def test_make_rows():
    keymap = Keymap(None)
    defaultkeys.map(keymap)

    # make sure that we don't crash if a default binding is missing.
    keymap.unbind(keymap.binding_for_help("View event log"))

    qh = quickhelp.make(HelpView, None, True)
    assert qh.make_rows(keymap)
