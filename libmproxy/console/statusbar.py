import os.path

import urwid

import netlib.utils
from . import pathedit, signals, common


class ActionBar(urwid.WidgetWrap):

    def __init__(self):
        urwid.WidgetWrap.__init__(self, None)
        self.clear()
        signals.status_message.connect(self.sig_message)
        signals.status_prompt.connect(self.sig_prompt)
        signals.status_prompt_path.connect(self.sig_path_prompt)
        signals.status_prompt_onekey.connect(self.sig_prompt_onekey)

        self.last_path = ""

        self.prompting = False
        self.onekey = False
        self.pathprompt = False

    def sig_message(self, sender, message, expire=None):
        w = urwid.Text(message)
        self._w = w
        self.prompting = False
        if expire:
            def cb(*args):
                if w == self._w:
                    self.clear()
            signals.call_in.send(seconds=expire, callback=cb)

    def prep_prompt(self, p):
        return p.strip() + ": "

    def sig_prompt(self, sender, prompt, text, callback, args=()):
        signals.focus.send(self, section="footer")
        self._w = urwid.Edit(self.prep_prompt(prompt), text or "")
        self.prompting = (callback, args)

    def sig_path_prompt(self, sender, prompt, callback, args=()):
        signals.focus.send(self, section="footer")
        self._w = pathedit.PathEdit(
            self.prep_prompt(prompt),
            os.path.dirname(self.last_path)
        )
        self.pathprompt = True
        self.prompting = (callback, args)

    def sig_prompt_onekey(self, sender, prompt, keys, callback, args=()):
        """
            Keys are a set of (word, key) tuples. The appropriate key in the
            word is highlighted.
        """
        signals.focus.send(self, section="footer")
        prompt = [prompt, " ("]
        mkup = []
        for i, e in enumerate(keys):
            mkup.extend(common.highlight_key(e[0], e[1]))
            if i < len(keys) - 1:
                mkup.append(",")
        prompt.extend(mkup)
        prompt.append(")? ")
        self.onekey = set(i[1] for i in keys)
        self._w = urwid.Edit(prompt, "")
        self.prompting = (callback, args)

    def selectable(self):
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
                self.prompt_execute(self._w.get_edit_text())
            else:
                if common.is_keypress(k):
                    self._w.keypress(size, k)
                else:
                    return k

    def clear(self):
        self._w = urwid.Text("")
        self.prompting = False

    def prompt_done(self):
        self.prompting = False
        self.onekey = False
        self.pathprompt = False
        signals.status_message.send(message="")
        signals.focus.send(self, section="body")

    def prompt_execute(self, txt):
        if self.pathprompt:
            self.last_path = txt
        p, args = self.prompting
        self.prompt_done()
        msg = p(txt, *args)
        if msg:
            signals.status_message.send(message=msg, expire=1)


class StatusBar(urwid.WidgetWrap):

    def __init__(self, master, helptext):
        self.master, self.helptext = master, helptext
        self.ab = ActionBar()
        self.ib = urwid.WidgetWrap(urwid.Text(""))
        self._w = urwid.Pile([self.ib, self.ab])
        signals.update_settings.connect(self.sig_update_settings)
        signals.flowlist_change.connect(self.sig_update_settings)
        self.redraw()

    def sig_update_settings(self, sender):
        self.redraw()

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
            r.append(":%s to go]" % self.master.client_playback.count())
        if self.master.server_playback:
            r.append("[")
            r.append(("heading_key", "splayback"))
            if self.master.nopop:
                r.append(":%s in file]" % self.master.server_playback.count())
            else:
                r.append(":%s to go]" % self.master.server_playback.count())
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
            r.append(":%s]" % self.master.state.intercept_txt)
        if self.master.state.limit_txt:
            r.append("[")
            r.append(("heading_key", "l"))
            r.append(":%s]" % self.master.state.limit_txt)
        if self.master.stickycookie_txt:
            r.append("[")
            r.append(("heading_key", "t"))
            r.append(":%s]" % self.master.stickycookie_txt)
        if self.master.stickyauth_txt:
            r.append("[")
            r.append(("heading_key", "u"))
            r.append(":%s]" % self.master.stickyauth_txt)
        if self.master.state.default_body_view.name != "Auto":
            r.append("[")
            r.append(("heading_key", "M"))
            r.append(":%s]" % self.master.state.default_body_view.name)

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
            opts.append(
                "stream:%s" % netlib.utils.pretty_size(
                    self.master.stream_large_bodies.max_size
                )
            )

        if opts:
            r.append("[%s]" % (":".join(opts)))

        if self.master.server.config.mode in ["reverse", "upstream"]:
            dst = self.master.server.config.upstream_server
            r.append("[dest:%s]" % netlib.utils.unparse_url(
                dst.scheme,
                dst.address.host,
                dst.address.port
            ))
        if self.master.scripts:
            r.append("[")
            r.append(("heading_key", "s"))
            r.append("cripts:%s]" % len(self.master.scripts))
        # r.append("[lt:%0.3f]"%self.master.looptime)

        if self.master.stream:
            r.append("[W:%s]" % self.master.stream_path)

        return r

    def redraw(self):
        fc = self.master.state.flow_count()
        if self.master.state.focus is None:
            offset = 0
        else:
            offset = min(self.master.state.focus + 1, fc)
        t = [
            ('heading', ("[%s/%s]" % (offset, fc)).ljust(9))
        ]

        if self.master.server.bound:
            host = self.master.server.address.host
            if host == "0.0.0.0":
                host = "*"
            boundaddr = "[%s:%s]" % (host, self.master.server.address.port)
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
