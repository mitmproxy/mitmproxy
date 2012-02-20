import urwid
import common

def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted connections"),
        ("a", "accept this intercepted connection"),
        ("C", "clear connection list or eventlog"),
        ("d", "delete flow"),
        ("D", "duplicate flow"),
        ("e", "toggle eventlog"),
        ("l", "set limit filter pattern"),
        ("L", "load saved flows"),
        ("r", "replay request"),
        ("V", "revert changes to request"),
        ("w", "save all flows matching current limit"),
        ("W", "save this flow"),
        ("X", "kill and delete connection, even if it's mid-intercept"),
        ("tab", "tab between eventlog and connection list"),
        ("enter", "view connection"),
        ("|", "run script on this flow"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()


class EventListBox(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        urwid.ListBox.__init__(self, master.eventlist)

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "C":
            self.master.clear_events()
            key = None
        return urwid.ListBox.keypress(self, size, key)


class BodyPile(urwid.Pile):
    def __init__(self, master):
        h = urwid.Text("Event log")
        h = urwid.Padding(h, align="left", width=("relative", 100))

        self.inactive_header = urwid.AttrWrap(h, "heading_inactive")
        self.active_header = urwid.AttrWrap(h, "heading")

        urwid.Pile.__init__(
            self,
            [
                ConnectionListBox(master),
                urwid.Frame(EventListBox(master), header = self.inactive_header)
            ]
        )
        self.master = master
        self.focus = 0

    def keypress(self, size, key):
        if key == "tab":
            self.focus = (self.focus + 1)%len(self.widget_list)
            self.set_focus(self.focus)
            if self.focus == 1:
                self.widget_list[1].header = self.active_header
            else:
                self.widget_list[1].header = self.inactive_header
            key = None
        elif key == "v":
            self.master.toggle_eventlog()
            key = None

        # This is essentially a copypasta from urwid.Pile's keypress handler.
        # So much for "closed for modification, but open for extension".
        item_rows = None
        if len(size)==2:
            item_rows = self.get_item_rows( size, focus=True )
        i = self.widget_list.index(self.focus_item)
        tsize = self.get_item_size(size,i,True,item_rows)
        return self.focus_item.keypress( tsize, key )


class ConnectionItem(common.WWrap):
    def __init__(self, master, state, flow, focus):
        self.master, self.state, self.flow = master, state, flow
        self.focus = focus
        w = self.get_text()
        common.WWrap.__init__(self, w)

    def get_text(self):
        return common.format_flow(self.flow, self.focus)

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
        elif key == "D":
            f = self.master.duplicate_flow(self.flow)
            self.master.currentflow = f
            self.master.focus_current()
        elif key == "r":
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.sync_list_view()
        elif key == "V":
            self.state.revert(self.flow)
            self.master.sync_list_view()
        elif key == "w":
            self.master.path_prompt(
                "Save flows: ",
                self.state.last_saveload,
                self.master.save_flows
            )
        elif key == "W":
            self.master.path_prompt(
                "Save this flow: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )
        elif key == "X":
            self.flow.kill(self.master)
        elif key == "enter":
            if self.flow.request:
                self.master.view_flow(self.flow)
        elif key == "|":
            self.master.path_prompt(
                "Send flow to script: ",
                self.state.last_script,
                self.master.run_script_once,
                self.flow
            )
        else:
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
        elif key == "C":
            self.master.clear_connections()
        elif key == "e":
            self.master.toggle_eventlog()
        elif key == "l":
            self.master.prompt("Limit: ", self.master.state.limit_txt, self.master.set_limit)
            self.master.sync_list_view()
        elif key == "L":
            self.master.path_prompt(
                "Load flows: ",
                self.master.state.last_saveload,
                self.master.load_flows_callback
            )
        else:
            return urwid.ListBox.keypress(self, size, key)
