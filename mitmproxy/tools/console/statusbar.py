from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

import urwid

import mitmproxy.tools.console.master
from mitmproxy.tools.console import commandexecutor
from mitmproxy.tools.console import common
from mitmproxy.tools.console import flowlist
from mitmproxy.tools.console import quickhelp
from mitmproxy.tools.console import signals
from mitmproxy.tools.console.commander import commander
from mitmproxy.utils import human


@lru_cache
def shorten_message(
    msg: tuple[str, str] | str, max_width: int
) -> list[tuple[str, str]]:
    """
    Shorten message so that it fits into a single line in the statusbar.
    """
    if isinstance(msg, tuple):
        disp_attr, msg_text = msg
    elif isinstance(msg, str):
        msg_text = msg
        disp_attr = ""
    else:
        raise AssertionError(f"Unexpected message type: {type(msg)}")
    msg_end = "\u2026"  # unicode ellipsis for the end of shortened message
    prompt = "(more in eventlog)"

    msg_lines = msg_text.split("\n")
    first_line = msg_lines[0]
    if len(msg_lines) > 1:
        # First line of messages with a few lines must end with prompt.
        line_length = len(first_line) + len(prompt)
    else:
        line_length = len(first_line)

    if line_length > max_width:
        shortening_index = max(0, max_width - len(prompt) - len(msg_end))
        first_line = first_line[:shortening_index] + msg_end
    else:
        if len(msg_lines) == 1:
            prompt = ""

    return [(disp_attr, first_line), ("warn", prompt)]


class ActionBar(urwid.WidgetWrap):
    def __init__(self, master: mitmproxy.tools.console.master.ConsoleMaster) -> None:
        self.master = master
        self.top = urwid.WidgetWrap(urwid.Text(""))
        self.bottom = urwid.WidgetWrap(urwid.Text(""))
        super().__init__(urwid.Pile([self.top, self.bottom]))
        self.show_quickhelp()
        signals.status_message.connect(self.sig_message)
        signals.status_prompt.connect(self.sig_prompt)
        signals.status_prompt_onekey.connect(self.sig_prompt_onekey)
        signals.status_prompt_command.connect(self.sig_prompt_command)
        signals.window_refresh.connect(self.sig_update)
        master.view.focus.sig_change.connect(self.sig_update)
        master.view.sig_view_update.connect(self.sig_update)

        self.prompting: Callable[[str], None] | None = None

        self.onekey: set[str] | None = None

    def sig_update(self, flow=None) -> None:
        if not self.prompting and flow is None or flow == self.master.view.focus.flow:
            self.show_quickhelp()

    def sig_message(
        self, message: tuple[str, str] | str, expire: int | None = 1
    ) -> None:
        if self.prompting:
            return
        cols, _ = self.master.ui.get_cols_rows()
        w = urwid.Text(shorten_message(message, cols))
        self.top._w = w
        self.bottom._w = urwid.Text("")
        if expire:

            def cb():
                if w == self.top._w:
                    self.show_quickhelp()

            signals.call_in.send(seconds=expire, callback=cb)

    def sig_prompt(
        self, prompt: str, text: str | None, callback: Callable[[str], None]
    ) -> None:
        signals.focus.send(section="footer")
        self.top._w = urwid.Edit(f"{prompt.strip()}: ", text or "")
        self.bottom._w = urwid.Text("")
        self.prompting = callback

    def sig_prompt_command(self, partial: str = "", cursor: int | None = None) -> None:
        signals.focus.send(section="footer")
        self.top._w = commander.CommandEdit(
            self.master,
            partial,
        )
        if cursor is not None:
            self.top._w.cbuf.cursor = cursor
        self.bottom._w = urwid.Text("")
        self.prompting = self.execute_command

    def execute_command(self, txt: str) -> None:
        if txt.strip():
            self.master.commands.call("commands.history.add", txt)
        execute = commandexecutor.CommandExecutor(self.master)
        execute(txt)

    def sig_prompt_onekey(
        self, prompt: str, keys: list[tuple[str, str]], callback: Callable[[str], None]
    ) -> None:
        """
        Keys are a set of (word, key) tuples. The appropriate key in the
        word is highlighted.
        """
        signals.focus.send(section="footer")
        parts = [prompt, " ("]
        mkup = []
        for i, e in enumerate(keys):
            mkup.extend(common.highlight_key(e[0], e[1]))
            if i < len(keys) - 1:
                mkup.append(",")
        parts.extend(mkup)
        parts.append(")? ")
        self.onekey = {i[1] for i in keys}
        self.top._w = urwid.Edit(parts, "")
        self.bottom._w = urwid.Text("")
        self.prompting = callback

    def selectable(self) -> bool:
        return True

    def keypress(self, size, k):
        if self.prompting:
            if k == "esc":
                self.prompt_done()
            elif self.onekey:
                if k == "enter":
                    self.prompt_done()
                elif k in self.onekey:
                    self.prompt_execute(k)
            elif k == "enter":
                text = self.top._w.get_edit_text()
                self.prompt_execute(text)
            else:
                if common.is_keypress(k):
                    self.top._w.keypress(size, k)
                else:
                    return k

    def show_quickhelp(self) -> None:
        if w := self.master.window:
            s = w.focus_stack()
            focused_widget = type(s.top_widget())
            is_top_widget = len(s.stack) == 1
        else:  # on startup
            focused_widget = flowlist.FlowListBox
            is_top_widget = True
        focused_flow = self.master.view.focus.flow
        qh = quickhelp.make(focused_widget, focused_flow, is_top_widget)
        self.top._w, self.bottom._w = qh.make_rows(self.master.keymap)

    def prompt_done(self) -> None:
        self.prompting = None
        self.onekey = None
        self.show_quickhelp()
        signals.focus.send(section="body")

    def prompt_execute(self, txt) -> None:
        callback = self.prompting
        assert callback is not None
        self.prompt_done()
        msg = callback(txt)
        if msg:
            signals.status_message.send(message=msg, expire=1)


class StatusBar(urwid.WidgetWrap):
    REFRESHTIME = 0.5  # Timed refresh time in seconds
    keyctx = ""

    def __init__(self, master: mitmproxy.tools.console.master.ConsoleMaster) -> None:
        self.master = master
        self.ib = urwid.WidgetWrap(urwid.Text(""))
        self.ab = ActionBar(self.master)
        super().__init__(urwid.Pile([self.ib, self.ab]))
        signals.flow_change.connect(self.sig_update)
        signals.update_settings.connect(self.sig_update)
        master.options.changed.connect(self.sig_update)
        master.view.focus.sig_change.connect(self.sig_update)
        master.view.sig_view_add.connect(self.sig_update)
        self.refresh()

    def refresh(self) -> None:
        self.redraw()
        signals.call_in.send(seconds=self.REFRESHTIME, callback=self.refresh)

    def sig_update(self, *args, **kwargs) -> None:
        self.redraw()

    def keypress(self, *args, **kwargs):
        return self.ab.keypress(*args, **kwargs)

    def get_status(self) -> list[tuple[str, str] | str]:
        r: list[tuple[str, str] | str] = []

        sreplay = self.master.commands.call("replay.server.count")
        creplay = self.master.commands.call("replay.client.count")

        if len(self.master.options.modify_headers):
            r.append("[")
            r.append(("heading_key", "H"))
            r.append("eaders]")
        if len(self.master.options.modify_body):
            r.append("[%d body modifications]" % len(self.master.options.modify_body))
        if creplay:
            r.append("[")
            r.append(("heading_key", "cplayback"))
            r.append(":%s]" % creplay)
        if sreplay:
            r.append("[")
            r.append(("heading_key", "splayback"))
            r.append(":%s]" % sreplay)
        if self.master.options.ignore_hosts:
            r.append("[")
            r.append(("heading_key", "I"))
            r.append("gnore:%d]" % len(self.master.options.ignore_hosts))
        elif self.master.options.allow_hosts:
            r.append("[")
            r.append(("heading_key", "A"))
            r.append("llow:%d]" % len(self.master.options.allow_hosts))
        if self.master.options.tcp_hosts:
            r.append("[")
            r.append(("heading_key", "T"))
            r.append("CP:%d]" % len(self.master.options.tcp_hosts))
        if self.master.options.intercept:
            r.append("[")
            if not self.master.options.intercept_active:
                r.append("X")
            r.append(("heading_key", "i"))
            r.append(":%s]" % self.master.options.intercept)
        if self.master.options.view_filter:
            r.append("[")
            r.append(("heading_key", "f"))
            r.append(":%s]" % self.master.options.view_filter)
        if self.master.options.stickycookie:
            r.append("[")
            r.append(("heading_key", "t"))
            r.append(":%s]" % self.master.options.stickycookie)
        if self.master.options.stickyauth:
            r.append("[")
            r.append(("heading_key", "u"))
            r.append(":%s]" % self.master.options.stickyauth)
        if self.master.options.console_default_contentview != "auto":
            r.append(
                "[contentview:%s]" % (self.master.options.console_default_contentview)
            )
        if self.master.options.has_changed("view_order"):
            r.append("[")
            r.append(("heading_key", "o"))
            r.append(":%s]" % self.master.options.view_order)

        opts = []
        if self.master.options.anticache:
            opts.append("anticache")
        if self.master.options.anticomp:
            opts.append("anticomp")
        if self.master.options.showhost:
            opts.append("showhost")
        if not self.master.options.server_replay_refresh:
            opts.append("norefresh")
        if not self.master.options.upstream_cert:
            opts.append("no-upstream-cert")
        if self.master.options.console_focus_follow:
            opts.append("following")
        if self.master.options.stream_large_bodies:
            opts.append(self.master.options.stream_large_bodies)

        if opts:
            r.append("[%s]" % (":".join(opts)))

        if self.master.options.mode != ["regular"]:
            if len(self.master.options.mode) == 1:
                r.append(f"[{self.master.options.mode[0]}]")
            else:
                r.append(f"[modes:{len(self.master.options.mode)}]")
        if self.master.options.scripts:
            r.append("[scripts:%s]" % len(self.master.options.scripts))

        if self.master.options.save_stream_file:
            r.append("[W:%s]" % self.master.options.save_stream_file)

        return r

    def redraw(self) -> None:
        fc = self.master.commands.execute("view.properties.length")
        if self.master.view.focus.index is None:
            offset = 0
        else:
            offset = self.master.view.focus.index + 1

        if self.master.options.view_order_reversed:
            arrow = common.SYMBOL_UP
        else:
            arrow = common.SYMBOL_DOWN

        marked = ""
        if self.master.commands.execute("view.properties.marked"):
            marked = "M"

        t: list[tuple[str, str] | str] = [
            ("heading", f"{arrow} {marked} [{offset}/{fc}]".ljust(11)),
        ]

        listen_addrs: list[str] = list(
            dict.fromkeys(
                human.format_address(a)
                for a in self.master.addons.get("proxyserver").listen_addrs()
            )
        )
        if listen_addrs:
            boundaddr = f"[{', '.join(listen_addrs)}]"
        else:
            boundaddr = ""
        t.extend(self.get_status())
        status = urwid.AttrMap(
            urwid.Columns(
                [
                    urwid.Text(t),
                    urwid.Text(boundaddr, align="right"),
                ]
            ),
            "heading",
        )
        self.ib._w = status

    def selectable(self) -> bool:
        return True
