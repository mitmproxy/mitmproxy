from __future__ import absolute_import
import urwid
from . import common

def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted flows"),
        ("a", "accept this intercepted flow"),
        ("C", "clear flow list or eventlog"),
        ("d", "delete flow"),
        ("D", "duplicate flow"),
        ("e", "toggle eventlog"),
        ("F", "toggle follow flow list"),
        ("l", "set limit filter pattern"),
        ("L", "load saved flows"),
        ("r", "replay request"),
        ("V", "revert changes to request"),
        ("w", "save flows "),
        ("W", "stream flows to file"),
        ("X", "kill and delete flow, even if it's mid-intercept"),
        ("tab", "tab between eventlog and flow list"),
        ("enter", "view flow"),
        ("|", "run script on this flow"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()

footer = [
    ('heading_key', "?"), ":help ",
]

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
                FlowListBox(master),
                urwid.Frame(EventListBox(master), header = self.inactive_header)
            ]
        )
        self.master = master

    def keypress(self, size, key):
        if key == "tab":
            self.focus_position = (self.focus_position + 1)%len(self.widget_list)
            if self.focus_position == 1:
                self.widget_list[1].header = self.active_header
            else:
                self.widget_list[1].header = self.inactive_header
            key = None
        elif key == "e":
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
        self.f = focus
        w = self.get_text()
        common.WWrap.__init__(self, w)

    def get_text(self):
        return common.format_flow(self.flow, self.f, hostheader=self.master.showhost)

    def selectable(self):
        return True

    def save_flows_prompt(self, k):
        if k == "a":
            self.master.path_prompt(
                "Save all flows to: ",
                self.state.last_saveload,
                self.master.save_flows
            )
        else:
            self.master.path_prompt(
                "Save this flow to: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )

    def stop_server_playback_prompt(self, a):
        if a != "n":
            self.master.stop_server_playback()

    def server_replay_prompt(self, k):
        if k == "a":
            self.master.start_server_playback(
                [i.copy() for i in self.master.state.view],
                self.master.killextra, self.master.rheaders,
                False, self.master.nopop,
                self.master.options.replay_ignore_params, self.master.options.replay_ignore_content
            )
        elif k == "t":
            self.master.start_server_playback(
                [self.flow.copy()],
                self.master.killextra, self.master.rheaders,
                False, self.master.nopop,
                self.master.options.replay_ignore_params, self.master.options.replay_ignore_content
            )
        else:
            self.master.path_prompt(
                "Server replay path: ",
                self.state.last_saveload,
                self.master.server_playback_path
            )

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
            self.master.view_flow(f)
        elif key == "r":
            self.flow.backup()
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.sync_list_view()
        elif key == "S":
            if not self.master.server_playback:
                self.master.prompt_onekey(
                    "Server Replay",
                    (
                        ("all flows", "a"),
                        ("this flow", "t"),
                        ("file", "f"),
                    ),
                    self.server_replay_prompt,
                )
            else:
                self.master.prompt_onekey(
                    "Stop current server replay?",
                    (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    self.stop_server_playback_prompt,
                )
        elif key == "V":
            if not self.flow.modified():
                self.master.statusbar.message("Flow not modified.")
                return
            self.state.revert(self.flow)
            self.master.sync_list_view()
            self.master.statusbar.message("Reverted.")
        elif key == "w":
            self.master.prompt_onekey(
                "Save",
                (
                    ("all flows", "a"),
                    ("this flow", "t"),
                ),
                self.save_flows_prompt,
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


class FlowListWalker(urwid.ListWalker):
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
        return ret

    def get_next(self, pos):
        f, i = self.state.get_next(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i

    def get_prev(self, pos):
        f, i = self.state.get_prev(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i


class FlowListBox(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        urwid.ListBox.__init__(self, master.flow_list_walker)

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "A":
            self.master.accept_all()
            self.master.sync_list_view()
        elif key == "C":
            self.master.clear_flows()
        elif key == "e":
            self.master.toggle_eventlog()
        elif key == "l":
            self.master.prompt("Limit: ", self.master.state.limit_txt, self.master.set_limit)
        elif key == "L":
            self.master.path_prompt(
                "Load flows: ",
                self.master.state.last_saveload,
                self.master.load_flows_callback
            )
        elif key == "F":
            self.master.toggle_follow_flows()
        elif key == "W":
            if self.master.stream:
                self.master.stop_stream()
            else:
                self.master.path_prompt(
                    "Stream flows to: ",
                    self.master.state.last_saveload,
                    self.master.start_stream
                )
        else:
            return urwid.ListBox.keypress(self, size, key)
