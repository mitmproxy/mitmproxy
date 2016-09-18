from __future__ import absolute_import, print_function, division

import urwid

from mitmproxy import contentviews
from mitmproxy.console import common
from mitmproxy.console import grideditor
from mitmproxy.console import palettes
from mitmproxy.console import select
from mitmproxy.console import signals

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


class Options(urwid.WidgetWrap):

    def __init__(self, master):
        self.master = master
        self.lb = select.Select(
            [
                select.Heading("Traffic Manipulation"),
                select.Option(
                    "Header Set Patterns",
                    "H",
                    lambda: len(master.options.setheaders),
                    self.setheaders
                ),
                select.Option(
                    "Ignore Patterns",
                    "I",
                    lambda: master.options.ignore_hosts,
                    self.ignore_hosts
                ),
                select.Option(
                    "Replacement Patterns",
                    "R",
                    lambda: len(master.options.replacements),
                    self.replacepatterns
                ),
                select.Option(
                    "Scripts",
                    "S",
                    lambda: master.options.scripts,
                    self.scripts
                ),

                select.Heading("Interface"),
                select.Option(
                    "Default Display Mode",
                    "M",
                    self.has_default_displaymode,
                    self.default_displaymode
                ),
                select.Option(
                    "Palette",
                    "P",
                    lambda: self.master.palette != palettes.DEFAULT,
                    self.palette
                ),
                select.Option(
                    "Show Host",
                    "w",
                    lambda: master.options.showhost,
                    master.options.toggler("showhost")
                ),

                select.Heading("Network"),
                select.Option(
                    "No Upstream Certs",
                    "U",
                    lambda: master.options.no_upstream_cert,
                    master.options.toggler("no_upstream_cert")
                ),
                select.Option(
                    "TCP Proxying",
                    "T",
                    lambda: master.options.tcp_hosts,
                    self.tcp_hosts
                ),
                select.Option(
                    "Don't Verify SSL/TLS Certificates",
                    "V",
                    lambda: master.options.ssl_insecure,
                    master.options.toggler("ssl_insecure")
                ),

                select.Heading("Utility"),
                select.Option(
                    "Anti-Cache",
                    "a",
                    lambda: master.options.anticache,
                    master.options.toggler("anticache")
                ),
                select.Option(
                    "Anti-Compression",
                    "o",
                    lambda: master.options.anticomp,
                    master.options.toggler("anticomp")
                ),
                select.Option(
                    "Kill Extra",
                    "x",
                    lambda: master.options.replay_kill_extra,
                    master.options.toggler("replay_kill_extra")
                ),
                select.Option(
                    "No Refresh",
                    "f",
                    lambda: not master.options.refresh_server_playback,
                    master.options.toggler("refresh_server_playback")
                ),
                select.Option(
                    "Sticky Auth",
                    "A",
                    lambda: master.options.stickyauth,
                    self.sticky_auth
                ),
                select.Option(
                    "Sticky Cookies",
                    "t",
                    lambda: master.options.stickycookie,
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
        super(Options, self).__init__(w)

        self.master.loop.widget.footer.update("")
        signals.update_settings.connect(self.sig_update_settings)
        master.options.changed.connect(self.sig_update_settings)

    def sig_update_settings(self, sender, updated=None):
        self.lb.walker._modified()

    def keypress(self, size, key):
        if key == "C":
            self.clearall()
            return None
        return super(self.__class__, self).keypress(size, key)

    def clearall(self):
        self.master.options.update(
            anticache = False,
            anticomp = False,
            ignore_hosts = (),
            tcp_hosts = (),
            replay_kill_extra = False,
            no_upstream_cert = False,
            refresh_server_playback = True,
            replacements = [],
            scripts = [],
            setheaders = [],
            showhost = False,
            stickyauth = None,
            stickycookie = None,
        )

        self.master.state.default_body_view = contentviews.get("Auto")

        signals.update_settings.send(self)
        signals.status_message.send(
            message = "All select.Options cleared",
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
        self.master.view_grideditor(
            grideditor.ScriptEditor(
                self.master,
                [[i] for i in self.master.options.scripts],
                self.master.edit_scripts
            )
        )

    def default_displaymode(self):
        signals.status_prompt_onekey.send(
            prompt = "Global default display mode",
            keys = contentviews.view_prompts,
            callback = self.master.change_default_display_mode
        )

    def has_default_displaymode(self):
        return self.master.state.default_body_view.name != "Auto"

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
