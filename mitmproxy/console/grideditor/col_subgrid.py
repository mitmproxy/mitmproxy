from __future__ import absolute_import, print_function, division
import urwid
from mitmproxy.console.grideditor import base
from mitmproxy.console import signals
from netlib.http import cookies


class Column(base.Column):
    def __init__(self, heading, subeditor):
        super(Column, self).__init__(heading)
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
        elif key in ["enter"]:
            editor.master.view_grideditor(
                self.subeditor(
                    editor.master,
                    editor.walker.get_current_value(),
                    editor.set_subeditor_value,
                    editor.walker.focus,
                    editor.walker.focus_col
                )
            )
        else:
            return key


class Display(base.Cell):
    def __init__(self, data):
        p = cookies._format_pairs(data, sep="\n")
        w = urwid.Text(p)
        super(Display, self).__init__(w)

    def get_data(self):
        pass
