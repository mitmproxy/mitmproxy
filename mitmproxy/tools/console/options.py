import urwid

from mitmproxy import contentviews
from mitmproxy.tools.console import common
from mitmproxy.tools.console import grideditor
from mitmproxy.tools.console import select
from mitmproxy.tools.console import signals

footer = [
    ('heading_key', "enter/space"), ":toggle ",
    ('heading_key', "C"), ":clear all ",
    ('heading_key', "W"), ":save ",
]


def _mkhelp():
    text = []
    keys = [
        ("enter/space", "activate option"),
        ("C", "clear all options"),
        ("w", "save options"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text


help_context = _mkhelp()


def checker(opt, options):
    def _check():
        return options.has_changed(opt)
    return _check


class Options(urwid.WidgetWrap):

    def __init__(self, master):
        self.master = master
        self.lb = select.Select(
            [
                select.Heading("Traffic Manipulation"),
                select.Option(
                    "Header Set Patterns",
                    "H",
                    checker("setheaders", master.options),
                    self.setheaders
                ),
                select.Option(
                    "Ignore Patterns",
                    "I",
                    checker("ignore_hosts", master.options),
                    self.ignore_hosts
                ),
                select.Option(
                    "Replacement Patterns",
                    "R",
                    checker("replacements", master.options),
                    self.replacepatterns
                ),
                select.Option(
                    "Scripts",
                    "S",
                    checker("scripts", master.options),
                    self.scripts
                ),

                select.Heading("Interface"),
                select.Option(
                    "Default Display Mode",
                    "M",
                    checker("default_contentview", master.options),
                    self.default_displaymode
                ),
                select.Option(
                    "Palette",
                    "P",
                    checker("palette", master.options),
                    self.palette
                ),
                select.Option(
                    "Show Host",
                    "w",
                    checker("showhost", master.options),
                    master.options.toggler("showhost")
                ),

                select.Heading("Network"),
                select.Option(
                    "No Upstream Certs",
                    "U",
                    checker("no_upstream_cert", master.options),
                    master.options.toggler("no_upstream_cert")
                ),
                select.Option(
                    "TCP Proxying",
                    "T",
                    checker("tcp_hosts", master.options),
                    self.tcp_hosts
                ),
                select.Option(
                    "Don't Verify SSL/TLS Certificates",
                    "V",
                    checker("ssl_insecure", master.options),
                    master.options.toggler("ssl_insecure")
                ),

                select.Heading("Utility"),
                select.Option(
                    "Anti-Cache",
                    "a",
                    checker("anticache", master.options),
                    master.options.toggler("anticache")
                ),
                select.Option(
                    "Anti-Compression",
                    "o",
                    checker("anticomp", master.options),
                    master.options.toggler("anticomp")
                ),
                select.Option(
                    "Kill Extra",
                    "x",
                    checker("replay_kill_extra", master.options),
                    master.options.toggler("replay_kill_extra")
                ),
                select.Option(
                    "No Refresh",
                    "f",
                    checker("refresh_server_playback", master.options),
                    master.options.toggler("refresh_server_playback")
                ),
                select.Option(
                    "Sticky Auth",
                    "A",
                    checker("stickyauth", master.options),
                    self.sticky_auth
                ),
                select.Option(
                    "Sticky Cookies",
                    "t",
                    checker("stickycookie", master.options),
                    self.sticky_cookie
                ),
            ]
        )
        title = urwid.Text("Options")
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")
        w = urwid.Frame(
            self.lb,
            header = title
        )
        super().__init__(w)

        self.master.loop.widget.footer.update("")
        signals.update_settings.connect(self.sig_update_settings)
        master.options.changed.connect(self.sig_update_settings)

    def sig_update_settings(self, sender, updated=None):
        self.lb.walker._modified()

    def keypress(self, size, key):
        if key == "C":
            self.clearall()
            return None
        if key == "W":
            self.save()
            return None
        return super().keypress(size, key)

    def do_save(self, path):
        self.master.options.save(path)
        return "Saved"

    def save(self):
        signals.status_prompt_path.send(
            prompt = "Save options to file",
            callback = self.do_save
        )

    def clearall(self):
        self.master.options.reset()
        signals.update_settings.send(self)
        signals.status_message.send(
            message = "Options cleared",
            expire = 1
        )

    def setheaders(self):
        self.master.view_grideditor(
            grideditor.SetHeadersEditor(
                self.master,
                self.master.options.setheaders,
                self.master.options.setter("setheaders")
            )
        )

    def tcp_hosts(self):
        self.master.view_grideditor(
            grideditor.HostPatternEditor(
                self.master,
                self.master.options.tcp_hosts,
                self.master.options.setter("tcp_hosts")
            )
        )

    def ignore_hosts(self):
        self.master.view_grideditor(
            grideditor.HostPatternEditor(
                self.master,
                self.master.options.ignore_hosts,
                self.master.options.setter("ignore_hosts")
            )
        )

    def replacepatterns(self):
        self.master.view_grideditor(
            grideditor.ReplaceEditor(
                self.master,
                self.master.options.replacements,
                self.master.options.setter("replacements")
            )
        )

    def scripts(self):
        def edit_scripts(scripts):
            self.master.options.scripts = [x[0] for x in scripts]
        self.master.view_grideditor(
            grideditor.ScriptEditor(
                self.master,
                [[i] for i in self.master.options.scripts],
                edit_scripts
            )
        )

    def default_displaymode(self):
        signals.status_prompt_onekey.send(
            prompt = "Global default display mode",
            keys = contentviews.view_prompts,
            callback = self.change_default_display_mode
        )

    def change_default_display_mode(self, t):
        v = contentviews.get_by_shortcut(t)
        self.master.options.default_contentview = v.name
        if self.master.view.focus.flow:
            signals.flow_change.send(self, flow = self.master.view.focus.flow)

    def sticky_auth(self):
        signals.status_prompt.send(
            prompt = "Sticky auth filter",
            text = self.master.options.stickyauth,
            callback = self.master.options.setter("stickyauth")
        )

    def sticky_cookie(self):
        signals.status_prompt.send(
            prompt = "Sticky cookie filter",
            text = self.master.options.stickycookie,
            callback = self.master.options.setter("stickycookie")
        )

    def palette(self):
        self.master.view_palette_picker()
