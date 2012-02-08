import urwid
import common
from .. import filt

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
        return urwid.ListBox.keypress(self, size, key)

    def helptext(self):
        text = []
        text.append(("head", "Keys for this view:\n"))
        text.extend(self.help_context)

        text.append(("head", "\n\nMovement:\n"))
        keys = [
            ("j, k", "up, down"),
            ("h, l", "left, right (in some contexts)"),
            ("space", "page down"),
            ("pg up/down", "page up/down"),
            ("arrows", "up, down, left, right"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))

        text.append(("head", "\n\nGlobal keys:\n"))
        keys = [
            ("c", "client replay"),
            ("i", "set interception pattern"),

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

            ("q", "quit / return to connection list"),
            ("Q", "quit without confirm prompt"),
            ("s", "set/unset script"),
            ("S", "server replay"),
            ("t", "set sticky cookie expression"),
            ("u", "set sticky auth expression"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))

        text.append(("head", "\n\nFilter expressions:\n"))
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

        text.extend(
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
        examples = [
                ("google\.com", "Url containing \"google.com"),
                ("~q ~b test", "Requests where body contains \"test\""),
                ("!(~q & ~t \"text/html\")", "Anything but requests with a text/html content type."),
        ]
        text.extend(common.format_keyvals(examples, key="key", val="text", indent=4))
        return [urwid.Text(text)]

