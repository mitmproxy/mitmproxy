from __future__ import absolute_import, print_function, division

import platform

import urwid

from mitmproxy import flowfilter
from mitmproxy.console import common
from mitmproxy.console import signals

from netlib import version

footer = [
    ("heading", 'mitmproxy {} (Python {}) '.format(version.VERSION, platform.python_version())),
    ('heading_key', "q"), ":back ",
]


class HelpView(urwid.ListBox):

    def __init__(self, help_context):
        self.help_context = help_context or []
        urwid.ListBox.__init__(
            self,
            self.helptext()
        )

    def helptext(self):
        text = []
        text.append(urwid.Text([("head", "This view:\n")]))
        text.extend(self.help_context)

        text.append(urwid.Text([("head", "\n\nMovement:\n")]))
        keys = [
            ("j, k", "down, up"),
            ("h, l", "left, right (in some contexts)"),
            ("g, G", "go to beginning, end"),
            ("space", "page down"),
            ("pg up/down", "page up/down"),
            ("ctrl+b/ctrl+f", "page up/down"),
            ("arrows", "up, down, left, right"),
        ]
        text.extend(
            common.format_keyvals(
                keys,
                key="key",
                val="text",
                indent=4))

        text.append(urwid.Text([("head", "\n\nGlobal keys:\n")]))
        keys = [
            ("i", "set interception pattern"),
            ("o", "options"),
            ("q", "quit / return to previous page"),
            ("Q", "quit without confirm prompt"),
            ("R", "replay of requests/responses from file"),
        ]
        text.extend(
            common.format_keyvals(keys, key="key", val="text", indent=4)
        )

        text.append(urwid.Text([("head", "\n\nFilter expressions:\n")]))
        text.extend(common.format_keyvals(flowfilter.help, key="key", val="text", indent=4))

        text.append(
            urwid.Text(
                [
                    "\n",
                    ("text", "    Regexes are Python-style.\n"),
                    ("text", "    Regexes can be specified as quoted strings.\n"),
                    ("text", "    Header matching (~h, ~hq, ~hs) is against a string of the form \"name: value\".\n"),
                    ("text", "    Expressions with no operators are regex matches against URL.\n"),
                    ("text", "    Default binary operator is &.\n"),
                    ("head", "\n    Examples:\n"),
                ]
            )
        )
        examples = [
            ("google\.com", "Url containing \"google.com"),
            ("~q ~b test", "Requests where body contains \"test\""),
            ("!(~q & ~t \"text/html\")", "Anything but requests with a text/html content type."),
        ]
        text.extend(
            common.format_keyvals(examples, key="key", val="text", indent=4)
        )
        return text

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "q":
            signals.pop_view_state.send(self)
            return None
        elif key == "?":
            key = None
        elif key == "g":
            self.set_focus(0)
        elif key == "G":
            self.set_focus(len(self.body.contents))
        return urwid.ListBox.keypress(self, size, key)
