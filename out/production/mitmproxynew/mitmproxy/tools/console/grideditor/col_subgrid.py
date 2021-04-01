import urwid
from mitmproxy.tools.console.grideditor import base
from mitmproxy.tools.console import signals
from mitmproxy.net.http import cookies


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

    def keypress(self, key, editor):
        if key in "rRe":
            signals.status_message.send(
                self,
                message="Press enter to edit this field.",
                expire=1000
            )
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
