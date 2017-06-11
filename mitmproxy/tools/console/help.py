import platform

import urwid

from mitmproxy import flowfilter
from mitmproxy.tools.console import common
from mitmproxy.tools.console import layoutwidget

from mitmproxy import version

footer = [
    ("heading", 'mitmproxy {} (Python {}) '.format(version.VERSION, platform.python_version())),
    ('heading_key', "q"), ":back ",
]


class HelpView(urwid.ListBox, layoutwidget.LayoutWidget):
    title = "Help"
    keyctx = "help"

    def __init__(self, help_context):
        urwid.ListBox.__init__(
            self,
            self.helptext()
        )

    def helptext(self):
        text = []

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
        if key == "m_start":
            self.set_focus(0)
        elif key == "m_end":
            self.set_focus(len(self.body.contents))
        return urwid.ListBox.keypress(self, size, key)
