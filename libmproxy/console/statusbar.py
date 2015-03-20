
import time

import urwid

from . import pathedit, signals
from .. import utils



class ActionBar(urwid.WidgetWrap):
    def __init__(self):
        urwid.WidgetWrap.__init__(self, urwid.Text(""))
        signals.status_message.connect(self.message)

    def selectable(self):
        return True

    def path_prompt(self, prompt, text):
        self._w = pathedit.PathEdit(prompt, text)

    def prompt(self, prompt, text = ""):
        self._w = urwid.Edit(prompt, text or "")

    def message(self, sender, message, expire=None):
        self.expire = expire
        self._w = urwid.Text(message)


class StatusBar(urwid.WidgetWrap):
    def __init__(self, master, helptext):
        self.master, self.helptext = master, helptext
        self.ab = ActionBar()
        self.ib = urwid.WidgetWrap(urwid.Text(""))
        self._w = urwid.Pile([self.ib, self.ab])

    def keypress(self, *args, **kwargs):
        return self.ab.keypress(*args, **kwargs)

    def get_status(self):
        r = []

        if self.master.setheaders.count():
            r.append("[")
            r.append(("heading_key", "H"))
            r.append("eaders]")
        if self.master.replacehooks.count():
            r.append("[")
            r.append(("heading_key", "R"))
            r.append("eplacing]")
        if self.master.client_playback:
            r.append("[")
            r.append(("heading_key", "cplayback"))
            r.append(":%s to go]"%self.master.client_playback.count())
        if self.master.server_playback:
            r.append("[")
            r.append(("heading_key", "splayback"))
            if self.master.nopop:
                r.append(":%s in file]"%self.master.server_playback.count())
            else:
                r.append(":%s to go]"%self.master.server_playback.count())
        if self.master.get_ignore_filter():
            r.append("[")
            r.append(("heading_key", "I"))
            r.append("gnore:%d]" % len(self.master.get_ignore_filter()))
        if self.master.get_tcp_filter():
            r.append("[")
            r.append(("heading_key", "T"))
            r.append("CP:%d]" % len(self.master.get_tcp_filter()))
        if self.master.state.intercept_txt:
            r.append("[")
            r.append(("heading_key", "i"))
            r.append(":%s]"%self.master.state.intercept_txt)
        if self.master.state.limit_txt:
            r.append("[")
            r.append(("heading_key", "l"))
            r.append(":%s]"%self.master.state.limit_txt)
        if self.master.stickycookie_txt:
            r.append("[")
            r.append(("heading_key", "t"))
            r.append(":%s]"%self.master.stickycookie_txt)
        if self.master.stickyauth_txt:
            r.append("[")
            r.append(("heading_key", "u"))
            r.append(":%s]"%self.master.stickyauth_txt)
        if self.master.state.default_body_view.name != "Auto":
            r.append("[")
            r.append(("heading_key", "M"))
            r.append(":%s]"%self.master.state.default_body_view.name)

        opts = []
        if self.master.anticache:
            opts.append("anticache")
        if self.master.anticomp:
            opts.append("anticomp")
        if self.master.showhost:
            opts.append("showhost")
        if not self.master.refresh_server_playback:
            opts.append("norefresh")
        if self.master.killextra:
            opts.append("killextra")
        if self.master.server.config.no_upstream_cert:
            opts.append("no-upstream-cert")
        if self.master.state.follow_focus:
            opts.append("following")
        if self.master.stream_large_bodies:
            opts.append("stream:%s" % utils.pretty_size(self.master.stream_large_bodies.max_size))

        if opts:
            r.append("[%s]"%(":".join(opts)))

        if self.master.server.config.mode in ["reverse", "upstream"]:
            dst = self.master.server.config.mode.dst
            scheme = "https" if dst[0] else "http"
            if dst[1] != dst[0]:
                scheme += "2https" if dst[1] else "http"
            r.append("[dest:%s]"%utils.unparse_url(scheme, *dst[2:]))
        if self.master.scripts:
            r.append("[")
            r.append(("heading_key", "s"))
            r.append("cripts:%s]"%len(self.master.scripts))
        # r.append("[lt:%0.3f]"%self.master.looptime)

        if self.master.stream:
            r.append("[W:%s]"%self.master.stream_path)

        return r

    def redraw(self):
        fc = self.master.state.flow_count()
        if self.master.state.focus is None:
            offset = 0
        else:
            offset = min(self.master.state.focus + 1, fc)
        t = [
            ('heading', ("[%s/%s]"%(offset, fc)).ljust(9))
        ]

        if self.master.server.bound:
            host = self.master.server.address.host
            if host == "0.0.0.0":
                host = "*"
            boundaddr = "[%s:%s]"%(host, self.master.server.address.port)
        else:
            boundaddr = ""
        t.extend(self.get_status())
        status = urwid.AttrWrap(urwid.Columns([
            urwid.Text(t),
            urwid.Text(
                [
                    self.helptext,
                    boundaddr
                ],
                align="right"
            ),
        ]), "heading")
        self.ib._w = status

    def update(self, text):
        self.helptext = text
        self.redraw()
        self.master.loop.draw_screen()

    def selectable(self):
        return True

    def get_edit_text(self):
        return self.ab._w.get_edit_text()

    def path_prompt(self, prompt, text):
        return self.ab.path_prompt(prompt, text)

    def prompt(self, prompt, text = ""):
        self.ab.prompt(prompt, text)
