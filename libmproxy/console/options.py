import urwid

from . import common, signals

help_context = None


class OptionWidget(urwid.WidgetWrap):
    def __init__(self, option, text, active, focus):
        self.option = option
        opt = urwid.Text(text, align="center")
        if focus and active:
            opt = urwid.AttrWrap(opt, "option_active_selected")
        elif focus:
            opt = urwid.AttrWrap(opt, "option_selected")
        elif active:
            opt = urwid.AttrWrap(opt, "option_active")
        opt = urwid.Padding(opt, align="center", width=("relative", 20))
        urwid.WidgetWrap.__init__(self, opt)

    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


class OptionWalker(urwid.ListWalker):
    def __init__(self, options):
        urwid.ListWalker.__init__(self)
        self.options = options
        self.focus = 0
        signals.update_settings.connect(self.sig_update_settings)

    def sig_update_settings(self, sender):
        self._modified()

    def set_focus(self, pos):
        self.focus = pos

    def get_focus(self):
        return self.options[self.focus].render(True), self.focus

    def get_next(self, pos):
        if pos >= len(self.options)-1:
            return None, None
        return self.options[pos+1].render(False), pos+1

    def get_prev(self, pos):
        if pos <= 0:
            return None, None
        return self.options[pos-1].render(False), pos-1


class OptionListBox(urwid.ListBox):
    def __init__(self, options):
        urwid.ListBox.__init__(
            self,
            OptionWalker(options)
        )

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "enter":
            self.get_focus()[0].option.ativate()
            return None
        return super(self.__class__, self).keypress(size, key)


_neg = lambda: False
class Option:
    def __init__(self, text, getstate=None, ativate=None):
        self.text = text
        self.getstate = getstate or _neg
        self.ativate = ativate or _neg

    def render(self, focus):
        return OptionWidget(self, self.text, self.getstate(), focus)


class Options(urwid.WidgetWrap):
    def __init__(self, master):
        self.master = master
        self.lb = OptionListBox(
            [
                Option(
                    "Anti-Cache",
                    lambda: master.anticache,
                    self.toggle_anticache
                ),
                Option(
                    "Anti-Compression",
                    lambda: master.anticomp,
                    self.toggle_anticomp
                ),
                #Option("Header Set Patterns"),
                #Option("Ignore Patterns"),
                Option(
                    "Kill Extra",
                    lambda: master.killextra,
                    self.toggle_killextra
                ),
                #Option("Manage Scripts"),
                #Option("Replacement Patterns"),
                Option(
                    "Show Host",
                    lambda: master.showhost,
                    self.toggle_showhost
                ),
                #Option("Sticky Cookies"),
                #Option("Sticky Auth"),
                #Option("TCP Proxying"),
                Option(
                    "No Refresh",
                    lambda: not master.refresh_server_playback,
                    self.toggle_refresh_server_playback
                ),
                Option(
                    "No Upstream Certs",
                    lambda: master.server.config.no_upstream_cert,
                    self.toggle_upstream_cert
                ),
            ]
        )
        title = urwid.Text("Options")
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")
        self._w = urwid.Frame(
            self.lb,
            header = title
        )
        self.master.loop.widget.footer.update("")

    def toggle_anticache(self):
        self.master.anticache = not self.master.anticache

    def toggle_anticomp(self):
        self.master.anticomp = not self.master.anticomp

    def toggle_killextra(self):
        self.master.killextra = not self.master.killextra

    def toggle_showhost(self):
        self.master.showhost = not self.master.showhost

    def toggle_refresh_server_playback(self):
        self.master.refresh_server_playback = not self.master.refresh_server_playback

    def toggle_upstream_cert(self):
        self.master.server.config.no_upstream_cert = not self.master.server.config.no_upstream_cert
        signals.update_settings.send(self)
