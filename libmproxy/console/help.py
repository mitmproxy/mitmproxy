# Copyright (C) 2012  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urwid
import common
from .. import filt, version

footer = [
    ("heading", 'mitmproxy v%s '%version.VERSION),
    ('heading_key', "q"), ":back ",
]

class HelpView(urwid.ListBox):
    def __init__(self, master, help_context, state):
        self.master, self.state = master, state
        self.help_context = help_context or []
        urwid.ListBox.__init__(
            self,
            self.helptext()
        )

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "q":
            self.master.statusbar = self.state[0]
            self.master.body = self.state[1]
            self.master.header = self.state[2]
            self.master.make_view()
            return None
        elif key == "?":
            key = None
        return urwid.ListBox.keypress(self, size, key)

    def helptext(self):
        text = []
        text.append(urwid.Text([("head", "Keys for this view:\n")]))
        text.extend(self.help_context)

        text.append(urwid.Text([("head", "\n\nMovement:\n")]))
        keys = [
            ("j, k", "up, down"),
            ("h, l", "left, right (in some contexts)"),
            ("space", "page down"),
            ("pg up/down", "page up/down"),
            ("arrows", "up, down, left, right"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))

        text.append(urwid.Text([("head", "\n\nGlobal keys:\n")]))
        keys = [
            ("c", "client replay"),
            ("i", "set interception pattern"),
            ("M", "change global default display mode"),
                (None,
                    common.highlight_key("automatic", "a") +
                    [("text", ": automatic detection")]
                ),
                (None,
                    common.highlight_key("hex", "h") +
                    [("text", ": Hex")]
                ),
                (None,
                    common.highlight_key("image", "i") +
                    [("text", ": Image")]
                ),
                (None,
                    common.highlight_key("javascript", "j") +
                    [("text", ": JavaScript")]
                ),
                (None,
                    common.highlight_key("json", "s") +
                    [("text", ": JSON")]
                ),
                (None,
                    common.highlight_key("urlencoded", "u") +
                    [("text", ": URL-encoded data")]
                ),
                (None,
                    common.highlight_key("raw", "r") +
                    [("text", ": raw data")]
                ),
                (None,
                    common.highlight_key("xml", "x") +
                    [("text", ": XML")]
                ),
            ("o", "toggle options:"),
                (None,
                    common.highlight_key("anticache", "a") +
                    [("text", ": prevent cached responses")]
                ),
                (None,
                    common.highlight_key("anticomp", "c") +
                    [("text", ": prevent compressed responses")]
                ),
                (None,
                    common.highlight_key("killextra", "k") +
                    [("text", ": kill requests not part of server replay")]
                ),
                (None,
                    common.highlight_key("norefresh", "n") +
                    [("text", ": disable server replay response refresh")]
                ),
                (None,
                    common.highlight_key("upstream certs", "u") +
                    [("text", ": sniff cert info from upstream server")]
                ),

            ("q", "quit / return to flow list"),
            ("Q", "quit without confirm prompt"),
            ("P", "set reverse proxy mode"),
            ("R", "edit replacement patterns"),
            ("s", "set/unset script"),
            ("S", "server replay"),
            ("t", "set sticky cookie expression"),
            ("u", "set sticky auth expression"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))

        text.append(urwid.Text([("head", "\n\nFilter expressions:\n")]))
        f = []
        for i in filt.filt_unary:
            f.append(
                ("~%s"%i.code, i.help)
            )
        for i in filt.filt_rex:
            f.append(
                ("~%s regex"%i.code, i.help)
            )
        for i in filt.filt_int:
            f.append(
                ("~%s int"%i.code, i.help)
            )
        f.sort()
        f.extend(
            [
                ("!", "unary not"),
                ("&", "and"),
                ("|", "or"),
                ("(...)", "grouping"),
            ]
        )
        text.extend(common.format_keyvals(f, key="key", val="text", indent=4))

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
        text.extend(common.format_keyvals(examples, key="key", val="text", indent=4))
        return text

