import urwid

from . import common, signals, grideditor

footer = [
    ('heading_key', "enter/space"), ":toggle ",
    ('heading_key', "C"), ":clear all ",
]

def _mkhelp():
    text = []
    keys = [
        ("enter/space", "activate option"),
        ("C", "clear all options"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()


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
            textattr = textattr,
            keyattr = keyattr
        )
        opt = urwid.Text(text, align="left")
        opt = urwid.AttrWrap(opt, textattr)
        opt = urwid.Padding(opt, align = "center", width = 40)
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
            if hasattr(i, "shortcut"):
                if i.shortcut in self.keymap:
                    raise ValueError("Duplicate shortcut key: %s"%i.shortcut)
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



class Heading:
    def __init__(self, text):
        self.text = text

    def render(self, focus):
        opt = urwid.Text("\n" + self.text, align="left")
        opt = urwid.AttrWrap(opt, "title")
        opt = urwid.Padding(opt, align = "center", width = 40)
        return opt


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
                Heading("Traffic Manipulation"),
                Option(
                    "Header Set Patterns",
                    "H",
                    lambda: master.setheaders.count(),
                    self.setheaders
                ),
                Option(
                    "Ignore Patterns",
                    "I"
                ),
                Option(
                    "Replacement Patterns",
                    "R"
                ),
                Option(
                    "Scripts",
                    "S"
                ),

                Heading("Interface"),
                Option(
                    "Default Display Mode",
                    "M"
                ),
                Option(
                    "Show Host",
                    "w",
                    lambda: master.showhost,
                    self.toggle_showhost
                ),

                Heading("Network"),
                Option(
                    "No Upstream Certs",
                    "U",
                    lambda: master.server.config.no_upstream_cert,
                    self.toggle_upstream_cert
                ),
                Option(
                    "TCP Proxying",
                    "T"
                ),

                Heading("Utility"),
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
                Option(
                    "Kill Extra",
                    "x",
                    lambda: master.killextra,
                    self.toggle_killextra
                ),
                Option(
                    "No Refresh",
                    "f",
                    lambda: not master.refresh_server_playback,
                    self.toggle_refresh_server_playback
                ),
                Option(
                    "Sticky Auth",
                    "A"
                ),
                Option(
                    "Sticky Cookies",
                    "t"
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
        self.master.setheaders.clear()
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

    def setheaders(self):
        def _set(*args, **kwargs):
            self.master.setheaders.set(*args, **kwargs)
            signals.update_settings.send(self)
        self.master.view_grideditor(
            grideditor.SetHeadersEditor(
                self.master,
                self.master.setheaders.get_specs(),
                _set
            )
        )
