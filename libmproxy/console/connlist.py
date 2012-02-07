import urwid
import common

class ConnectionItem(common.WWrap):
    def __init__(self, master, state, flow, focus):
        self.master, self.state, self.flow = master, state, flow
        self.focus = focus
        w = self.get_text()
        common.WWrap.__init__(self, w)

    def get_text(self):
        return urwid.Text(common.format_flow(self.flow, self.focus))

    def selectable(self):
        return True

    def keypress(self, (maxcol,), key):
        key = common.shortcuts(key)
        if key == "a":
            self.flow.accept_intercept()
            self.master.sync_list_view()
        elif key == "d":
            self.flow.kill(self.master)
            self.state.delete_flow(self.flow)
            self.master.sync_list_view()
        elif key == "r":
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.sync_list_view()
        elif key == "R":
            self.state.revert(self.flow)
            self.master.sync_list_view()
        elif key == "W":
            self.master.path_prompt(
                "Save this flow: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )
        elif key == "X":
            self.flow.kill(self.master)
        elif key == "v":
            self.master.toggle_eventlog()
        elif key == "enter":
            if self.flow.request:
                self.master.view_flow(self.flow)
        elif key == "|":
            self.master.path_prompt(
                "Send flow to script: ", self.state.last_script,
                self.master.run_script_once, self.flow
            )
        return key


class ConnectionListView(urwid.ListWalker):
    def __init__(self, master, state):
        self.master, self.state = master, state
        if self.state.flow_count():
            self.set_focus(0)

    def get_focus(self):
        f, i = self.state.get_focus()
        f = ConnectionItem(self.master, self.state, f, True) if f else None
        return f, i

    def set_focus(self, focus):
        ret = self.state.set_focus(focus)
        self._modified()
        return ret

    def get_next(self, pos):
        f, i = self.state.get_next(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i

    def get_prev(self, pos):
        f, i = self.state.get_prev(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i


class ConnectionListBox(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        urwid.ListBox.__init__(self, master.conn_list_view)

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "A":
            self.master.accept_all()
            self.master.sync_list_view()
            key = None
        elif key == "C":
            self.master.clear_connections()
            key = None
        elif key == "v":
            self.master.toggle_eventlog()
            key = None
        return urwid.ListBox.keypress(self, size, key)
