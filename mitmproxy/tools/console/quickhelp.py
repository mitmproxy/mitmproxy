"""
This module is reponsible for drawing the quick key help at the bottom of mitmproxy.
"""

from dataclasses import dataclass
from typing import Union

import urwid

from mitmproxy import flow
from mitmproxy.http import HTTPFlow
from mitmproxy.tools.console.eventlog import EventLog
from mitmproxy.tools.console.flowlist import FlowListBox
from mitmproxy.tools.console.flowview import FlowView
from mitmproxy.tools.console.grideditor.base import FocusEditor
from mitmproxy.tools.console.help import HelpView
from mitmproxy.tools.console.keybindings import KeyBindings
from mitmproxy.tools.console.keymap import Keymap
from mitmproxy.tools.console.options import Options


@dataclass
class BasicKeyHelp:
    """Quick help for urwid-builtin keybindings (i.e. those keys that do not appear in the keymap)"""

    key: str


HelpItems = dict[str, Union[str, BasicKeyHelp]]
"""
A mapping from the short text that should be displayed in the help bar to the full help text provided for the key
binding. The order of the items in the dictionary determines the order in which they are displayed in the help bar.

Some help items explain builtin urwid functionality, so there is no key binding for them. In this case, the value
is a BasicKeyHelp object.
"""


@dataclass
class QuickHelp:
    top_label: str
    top_items: HelpItems
    bottom_label: str
    bottom_items: HelpItems

    def make_rows(self, keymap: Keymap) -> tuple[urwid.Columns, urwid.Columns]:
        top = _make_row(self.top_label, self.top_items, keymap)
        bottom = _make_row(self.bottom_label, self.bottom_items, keymap)
        return top, bottom


def make(
    widget: type[urwid.Widget],
    focused_flow: flow.Flow | None,
    is_root_widget: bool,
) -> QuickHelp:
    top_label = ""
    top_items: HelpItems = {}
    if widget in (FlowListBox, FlowView):
        top_label = "Flow:"
        if focused_flow:
            if widget == FlowListBox:
                top_items["Select"] = "Select"
            else:
                top_items["Edit"] = "Edit a flow component"
            top_items |= {
                "Duplicate": "Duplicate flow",
                "Replay": "Replay this flow",
                "Export": "Export this flow to file",
                "Delete": "Delete flow from view",
            }
            if widget == FlowListBox:
                if focused_flow.marked:
                    top_items["Unmark"] = "Toggle mark on this flow"
                else:
                    top_items["Mark"] = "Toggle mark on this flow"
                top_items["Edit"] = "Edit a flow component"
            if focused_flow.intercepted:
                top_items["Resume"] = "Resume this intercepted flow"
            if focused_flow.modified():
                top_items["Restore"] = "Revert changes to this flow"
            if isinstance(focused_flow, HTTPFlow) and focused_flow.response:
                top_items["Save body"] = "Save response body to file"
            if widget == FlowView:
                top_items |= {
                    "Next flow": "Go to next flow",
                    "Prev flow": "Go to previous flow",
                }
        else:
            top_items |= {
                "Load flows": "Load flows from file",
                "Create new": "Create a new flow",
            }
    elif widget == KeyBindings:
        top_label = "Keybindings:"
        top_items |= {
            "Add": "Add a key binding",
            "Edit": "Edit the currently focused key binding",
            "Delete": "Unbind the currently focused key binding",
            "Execute": "Execute the currently focused key binding",
        }
    elif widget == Options:
        top_label = "Options:"
        top_items |= {
            "Edit": BasicKeyHelp("⏎"),
            "Reset": "Reset this option",
            "Reset all": "Reset all options",
            "Load file": "Load from file",
            "Save file": "Save to file",
        }
    elif widget == HelpView:
        top_label = "Help:"
        top_items |= {
            "Scroll down": BasicKeyHelp("↓"),
            "Scroll up": BasicKeyHelp("↑"),
            "Exit help": "Exit help",
            "Next tab": BasicKeyHelp("tab"),
        }
    elif widget == EventLog:
        top_label = "Events:"
        top_items |= {
            "Scroll down": BasicKeyHelp("↓"),
            "Scroll up": BasicKeyHelp("↑"),
            "Clear": "Clear",
        }
    elif issubclass(widget, FocusEditor):
        top_label = f"Edit:"
        top_items |= {
            "Start edit": BasicKeyHelp("⏎"),
            "Stop edit": BasicKeyHelp("esc"),
            "Add row": "Add a row after cursor",
            "Delete row": "Delete this row",
        }
    else:
        pass

    bottom_label = "Proxy:"
    bottom_items: HelpItems = {
        "Help": "View help",
    }
    if is_root_widget:
        bottom_items["Quit"] = "Exit the current view"
    else:
        bottom_items["Back"] = "Exit the current view"
    bottom_items |= {
        "Events": "View event log",
        "Options": "View options",
        "Intercept": "Set intercept",
        "Filter": "Set view filter",
    }
    if focused_flow:
        bottom_items |= {
            "Save flows": "Save listed flows to file",
            "Clear list": "Clear flow list",
        }
    bottom_items |= {
        "Layout": "Cycle to next layout",
        "Switch": "Focus next layout pane",
        "Follow new": "Set focus follow",
    }

    label_len = max(len(top_label), len(bottom_label), 8) + 1
    top_label = top_label.ljust(label_len)
    bottom_label = bottom_label.ljust(label_len)

    return QuickHelp(top_label, top_items, bottom_label, bottom_items)


def _make_row(label: str, items: HelpItems, keymap: Keymap) -> urwid.Columns:
    cols = [
        (len(label), urwid.Text(label)),
    ]
    for short, long in items.items():
        if isinstance(long, BasicKeyHelp):
            key_short = long.key
        else:
            b = keymap.binding_for_help(long)
            if b is None:
                continue
            key_short = b.key_short()
        txt = urwid.Text(
            [
                ("heading_inactive", key_short),
                " ",
                short,
            ],
            wrap="clip",
        )
        cols.append((14, txt))

    return urwid.Columns(cols)
