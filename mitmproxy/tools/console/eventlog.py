import urwid

from mitmproxy.tools.console import common


def _mkhelp():
    text = []
    keys = [("e", "toggle eventlog")]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text

help_context = _mkhelp()

footer = [
    ('heading_key', "e"), ":toggle ",
    ('heading_key', "?"), ":help ",
]

class EventLogHeader(urwid.WidgetWrap):

    def __init__(self):
        h = urwid.Text("Event log")
        h = urwid.Padding(h, align="left", width=("relative", 100))

        self.inactive_header = urwid.AttrWrap(h, "heading_inactive")
        self.active_header = urwid.AttrWrap(h, "heading")

        urwid.WidgetWrap.__init__(self, self.active_header)


class EventLogBox(urwid.ListBox):

    def __init__(self, master):
        self.master = master
        urwid.ListBox.__init__(self, master.logbuffer)

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "z":
            self.master.clear_events()
            key = None
        elif key == "G":
            self.set_focus(len(self.master.logbuffer) - 1)
        elif key == "g":
            self.set_focus(0)
        elif key == "F":
            o = self.master.options
            o.console_focus_follow = not o.console_focus_followel
        elif key == "e":
            self.master.toggle_eventlog()

        return urwid.ListBox.keypress(self, size, key)
