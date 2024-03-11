import urwid

from mitmproxy.net.http import cookies
from mitmproxy.tools.console import signals
from mitmproxy.tools.console.grideditor import base


class Column(base.Column):
    def __init__(self, heading, subeditor):
        super().__init__(heading)
        self.subeditor = subeditor

    def Edit(self, data):
        raise RuntimeError("SubgridColumn should handle edits itself")

    def Display(self, data):
        return Display(data)

    def blank(self):
        return []

    def keypress(self, key: str, editor):
        if key in "rRe":
            signals.status_message.send(message="Press enter to edit this field.")
            return
        elif key == "m_select":
            self.subeditor.grideditor = editor
            editor.master.switch_view("edit_focus_setcookie_attrs")
        else:
            return key


class Display(base.Cell):
    def __init__(self, data):
        p = cookies._format_pairs(data, sep="\n")
        w = urwid.Text(p)
        super().__init__(w)

    def get_data(self):
        pass
