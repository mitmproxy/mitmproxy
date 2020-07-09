import urwid

from mitmproxy import flowfilter
from mitmproxy.tools.console import common
from mitmproxy.tools.console import layoutwidget
from mitmproxy.tools.console import tabs


class CListBox(urwid.ListBox):
    def __init__(self, contents):
        self.length = len(contents)
        contents = contents[:] + [urwid.Text(["\n"])] * 5
        super().__init__(contents)

    def keypress(self, size, key):
        if key == "m_end":
            self.set_focus(self.length - 1)
        elif key == "m_start":
            self.set_focus(0)
        else:
            return super().keypress(size, key)


class HelpView(tabs.Tabs, layoutwidget.LayoutWidget):
    title = "Help"
    keyctx = "help"

    def __init__(self, master):
        self.master = master
        self.helpctx = ""
        super().__init__(
            [
                [self.keybindings_title, self.keybindings],
                [self.filtexp_title, self.filtexp],
            ]
        )

    def keybindings_title(self):
        return "Key Bindings"

    def format_keys(self, binds):
        kvs = []
        for b in binds:
            k = b.key
            if b.key == " ":
                k = "space"
            kvs.append((k, b.help or b.command))
        return common.format_keyvals(kvs)

    def keybindings(self):
        text = [
            urwid.Text(
                [
                    ("title", "Common Keybindings")
                ]
            )

        ]

        text.extend(self.format_keys(self.master.keymap.list("commonkey")))

        text.append(
            urwid.Text(
                [
                    "\n",
                    ("title", "Keybindings for this view")
                ]
            )
        )
        if self.helpctx:
            text.extend(self.format_keys(self.master.keymap.list(self.helpctx)))

        text.append(
            urwid.Text(
                [
                    "\n",
                    ("title", "Global Keybindings"),
                ]
            )
        )

        text.extend(self.format_keys(self.master.keymap.list("global")))

        return CListBox(text)

    def filtexp_title(self):
        return "Filter Expressions"

    def filtexp(self):
        text = []
        text.extend(common.format_keyvals(flowfilter.help, indent=4))
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
            (r"google\.com", r"Url containing \"google.com"),
            ("~q ~b test", r"Requests where body contains \"test\""),
            (r"!(~q & ~t \"text/html\")", "Anything but requests with a text/html content type."),
        ]
        text.extend(
            common.format_keyvals(examples, indent=4)
        )
        return CListBox(text)

    def layout_pushed(self, prev):
        """
            We are just about to push a window onto the stack.
        """
        self.helpctx = prev.keyctx
        self.show()
