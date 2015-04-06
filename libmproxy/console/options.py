import urwid

from . import common, signals

help_context = None
footer = [
    ('heading_key', "enter/space"), ":toggle ",
    ('heading_key', "C"), ":clear all ",
]


class OptionWidget(urwid.WidgetWrap):
    def __init__(self, option, text, shortcut, active, focus):
        self.option = option
        textattr = "text"
        keyattr = "key"
        if focus and active:
            textattr = "option_active_selected"
            keyattr = "option_selected_key"
        elif focus:
            textattr = "option_selected"
            keyattr = "option_selected_key"
        elif active:
            textattr = "option_active"
        text = common.highlight_key(
            text,
            shortcut,
            textattr=textattr,
            keyattr=keyattr
        )
        opt = urwid.Text(text, align="center")
        opt = urwid.AttrWrap(opt, textattr)
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
        self.options = options
        self.keymap = {}
        for i in options:
            self.keymap[i.shortcut] = i

    def keypress(self, size, key):
        if key == "enter" or key == " ":
            self.get_focus()[0].option.activate()
            return None
        key = common.shortcuts(key)
        if key in self.keymap:
            self.keymap[key].activate()
            self.set_focus(self.options.index(self.keymap[key]))
            return None
        return super(self.__class__, self).keypress(size, key)


_neg = lambda: False
class Option:
    def __init__(self, text, shortcut, getstate=None, activate=None):
        self.text = text
        self.shortcut = shortcut
        self.getstate = getstate or _neg
        self.activate = activate or _neg

    def render(self, focus):
        return OptionWidget(self, self.text, self.shortcut, self.getstate(), focus)


class Options(urwid.WidgetWrap):
    def __init__(self, master):
        self.master = master
        self.lb = OptionListBox(
            [
                Option(
                    "Anti-Cache",
                    "a",
                    lambda: master.anticache,
                    self.toggle_anticache
                ),
                Option(
                    "Anti-Compression",
                    "o",
                    lambda: master.anticomp,
                    self.toggle_anticomp
                ),
                #Option("Header Set Patterns"),
                #Option("Ignore Patterns"),
                Option(
                    "Kill Extra",
                    "E",
                    lambda: master.killextra,
                    self.toggle_killextra
                ),
                #Option("Manage Scripts"),
                #Option("Replacement Patterns"),
                Option(
                    "Show Host",
                    "H",
                    lambda: master.showhost,
                    self.toggle_showhost
                ),
                #Option("Sticky Cookies"),
                #Option("Sticky Auth"),
                #Option("TCP Proxying"),
                Option(
                    "No Refresh",
                    "R",
                    lambda: not master.refresh_server_playback,
                    self.toggle_refresh_server_playback
                ),
                Option(
                    "No Upstream Certs",
                    "U",
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

    def keypress(self, size, key):
        if key == "C":
            self.clearall()
            return None
        return super(self.__class__, self).keypress(size, key)

    def clearall(self):
        self.master.anticache = False
        self.master.anticomp = False
        self.master.killextra = False
        self.master.showhost = False
        self.master.refresh_server_playback = True
        self.master.server.config.no_upstream_cert = False
        signals.update_settings.send(self)
        signals.status_message.send(
            message = "All options cleared",
            expire = 1
        )

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
