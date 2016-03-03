from __future__ import absolute_import
import urwid

import netlib.utils

from . import common, signals


def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted flows"),
        ("a", "accept this intercepted flow"),
        ("b", "save request/response body"),
        ("C", "clear flow list or eventlog"),
        ("d", "delete flow"),
        ("D", "duplicate flow"),
        ("E", "export"),
        ("e", "toggle eventlog"),
        ("F", "toggle follow flow list"),
        ("l", "set limit filter pattern"),
        ("L", "load saved flows"),
        ("m", "toggle flow mark"),
        ("n", "create a new request"),
        ("P", "copy flow to clipboard"),
        ("r", "replay request"),
        ("U", "unmark all marked flows"),
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
        elif key == "G":
            self.set_focus(len(self.master.eventlist) - 1)
        elif key == "g":
            self.set_focus(0)
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
                urwid.Frame(
                    EventListBox(master),
                    header = self.inactive_header
                )
            ]
        )
        self.master = master

    def keypress(self, size, key):
        if key == "tab":
            self.focus_position = (
                self.focus_position + 1) % len(self.widget_list)
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
        if len(size) == 2:
            item_rows = self.get_item_rows(size, focus = True)
        i = self.widget_list.index(self.focus_item)
        tsize = self.get_item_size(size, i, True, item_rows)
        return self.focus_item.keypress(tsize, key)


class ConnectionItem(urwid.WidgetWrap):

    def __init__(self, master, state, flow, focus):
        self.master, self.state, self.flow = master, state, flow
        self.f = focus
        w = self.get_text()
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        return common.format_flow(
            self.flow,
            self.f,
            hostheader = self.master.showhost,
            marked=self.state.flow_marked(self.flow)
        )

    def selectable(self):
        return True

    def save_flows_prompt(self, k):
        if k == "a":
            signals.status_prompt_path.send(
                prompt = "Save all flows to",
                callback = self.master.save_flows
            )
        elif k == "m":
            signals.status_prompt_path.send(
                prompt = "Save marked flows to",
                callback = self.master.save_marked_flows
            )
        else:
            signals.status_prompt_path.send(
                prompt = "Save this flow to",
                callback = self.master.save_one_flow,
                args = (self.flow,)
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
                self.master.options.replay_ignore_params,
                self.master.options.replay_ignore_content,
                self.master.options.replay_ignore_payload_params,
                self.master.options.replay_ignore_host
            )
        elif k == "t":
            self.master.start_server_playback(
                [self.flow.copy()],
                self.master.killextra, self.master.rheaders,
                False, self.master.nopop,
                self.master.options.replay_ignore_params,
                self.master.options.replay_ignore_content,
                self.master.options.replay_ignore_payload_params,
                self.master.options.replay_ignore_host
            )
        else:
            signals.status_prompt_path.send(
                prompt = "Server replay path",
                callback = self.master.server_playback_path
            )

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            if self.flow.request:
                self.master.view_flow(self.flow)
                return True

    def keypress(self, xxx_todo_changeme, key):
        (maxcol,) = xxx_todo_changeme
        key = common.shortcuts(key)
        if key == "a":
            self.flow.accept_intercept(self.master)
            signals.flowlist_change.send(self)
        elif key == "d":
            self.flow.kill(self.master)
            self.state.delete_flow(self.flow)
            signals.flowlist_change.send(self)
        elif key == "D":
            f = self.master.duplicate_flow(self.flow)
            self.master.view_flow(f)
        elif key == "m":
            if self.state.flow_marked(self.flow):
                self.state.set_flow_marked(self.flow, False)
            else:
                self.state.set_flow_marked(self.flow, True)
            signals.flowlist_change.send(self)
        elif key == "r":
            r = self.master.replay_request(self.flow)
            if r:
                signals.status_message.send(message=r)
            signals.flowlist_change.send(self)
        elif key == "S":
            if not self.master.server_playback:
                signals.status_prompt_onekey.send(
                    prompt = "Server Replay",
                    keys = (
                        ("all flows", "a"),
                        ("this flow", "t"),
                        ("file", "f"),
                    ),
                    callback = self.server_replay_prompt,
                )
            else:
                signals.status_prompt_onekey.send(
                    prompt = "Stop current server replay?",
                    keys = (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    callback = self.stop_server_playback_prompt,
                )
        elif key == "U":
            for f in self.state.flows:
                self.state.set_flow_marked(f, False)
            signals.flowlist_change.send(self)
        elif key == "V":
            if not self.flow.modified():
                signals.status_message.send(message="Flow not modified.")
                return
            self.state.revert(self.flow)
            signals.flowlist_change.send(self)
            signals.status_message.send(message="Reverted.")
        elif key == "w":
            signals.status_prompt_onekey.send(
                self,
                prompt = "Save",
                keys = (
                    ("all flows", "a"),
                    ("this flow", "t"),
                    ("marked flows", "m"),
                ),
                callback = self.save_flows_prompt,
            )
        elif key == "X":
            self.flow.kill(self.master)
        elif key == "enter":
            if self.flow.request:
                self.master.view_flow(self.flow)
        elif key == "|":
            signals.status_prompt_path.send(
                prompt = "Send flow to script",
                callback = self.master.run_script_once,
                args = (self.flow,)
            )
        elif key == "P":
            common.ask_copy_part("a", self.flow, self.master, self.state)
        elif key == "E":
            signals.status_prompt_onekey.send(
                self,
                prompt = "Export",
                keys = (
                    ("as curl command", "c"),
                    ("as python code", "p"),
                    ("as raw request", "r"),
                    ("as locust code", "l"),
                    ("as locust task", "t"),
                ),
                callback = common.export_prompt,
                args = (self.flow,)
            )
        elif key == "b":
            common.ask_save_body(None, self.master, self.state, self.flow)
        else:
            return key


class FlowListWalker(urwid.ListWalker):

    def __init__(self, master, state):
        self.master, self.state = master, state
        signals.flowlist_change.connect(self.sig_flowlist_change)

    def sig_flowlist_change(self, sender):
        self._modified()

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
        urwid.ListBox.__init__(
            self,
            FlowListWalker(master, master.state)
        )

    def get_method_raw(self, k):
        if k:
            self.get_url(k)

    def get_method(self, k):
        if k == "e":
            signals.status_prompt.send(
                self,
                prompt = "Method",
                text = "",
                callback = self.get_method_raw
            )
        else:
            method = ""
            for i in common.METHOD_OPTIONS:
                if i[1] == k:
                    method = i[0].upper()
            self.get_url(method)

    def get_url(self, method):
        signals.status_prompt.send(
            prompt = "URL",
            text = "http://www.example.com/",
            callback = self.new_request,
            args = (method,)
        )

    def new_request(self, url, method):
        parts = netlib.utils.parse_url(str(url))
        if not parts:
            signals.status_message.send(message="Invalid Url")
            return
        scheme, host, port, path = parts
        f = self.master.create_request(method, scheme, host, port, path)
        self.master.view_flow(f)

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "A":
            self.master.accept_all()
            signals.flowlist_change.send(self)
        elif key == "C":
            self.master.clear_flows()
        elif key == "e":
            self.master.toggle_eventlog()
        elif key == "g":
            self.master.state.set_focus(0)
            signals.flowlist_change.send(self)
        elif key == "G":
            self.master.state.set_focus(self.master.state.flow_count())
            signals.flowlist_change.send(self)
        elif key == "l":
            signals.status_prompt.send(
                prompt = "Limit",
                text = self.master.state.limit_txt,
                callback = self.master.set_limit
            )
        elif key == "L":
            signals.status_prompt_path.send(
                self,
                prompt = "Load flows",
                callback = self.master.load_flows_callback
            )
        elif key == "n":
            signals.status_prompt_onekey.send(
                prompt = "Method",
                keys = common.METHOD_OPTIONS,
                callback = self.get_method
            )
        elif key == "F":
            self.master.toggle_follow_flows()
        elif key == "W":
            if self.master.stream:
                self.master.stop_stream()
            else:
                signals.status_prompt_path.send(
                    self,
                    prompt = "Stream flows to",
                    callback = self.master.start_stream_to_path
                )
        else:
            return urwid.ListBox.keypress(self, size, key)
