import urwid

class Window(urwid.Frame):
    def __init__(self, master, body, header, footer):
        urwid.Frame.__init__(self, body, header=header, footer=footer)
        self.master = master

    def keypress(self, size, k):
        if self.master.prompting:
            if k == "esc":
                self.master.prompt_cancel()
            elif self.master.onekey:
                if k == "enter":
                    self.master.prompt_cancel()
                elif k in self.master.onekey:
                    self.master.prompt_execute(k)
            elif k == "enter":
                self.master.prompt_execute()
            else:
                if common.is_keypress(k):
                    urwid.Frame.keypress(self, self.master.loop.screen_size, k)
                else:
                    return k
        else:
            k = urwid.Frame.keypress(self, self.master.loop.screen_size, k)
            if k == "?":
                self.master.view_help()
            elif k == "c":
                if not self.master.client_playback:
                    self.master.path_prompt(
                        "Client replay: ",
                        self.master.state.last_saveload,
                        self.master.client_playback_path
                    )
                else:
                    self.master.prompt_onekey(
                        "Stop current client replay?",
                        (
                            ("yes", "y"),
                            ("no", "n"),
                        ),
                        self.master.stop_client_playback_prompt,
                    )
            elif k == "H":
                self.master.view_grideditor(
                    grideditor.SetHeadersEditor(
                        self.master,
                        self.master.setheaders.get_specs(),
                        self.master.setheaders.set
                    )
                )
            elif k == "I":
                self.master.view_grideditor(
                    grideditor.HostPatternEditor(
                        self.master,
                        [[x] for x in self.master.get_ignore_filter()],
                        self.master.edit_ignore_filter
                    )
                )
            elif k == "T":
                self.master.view_grideditor(
                    grideditor.HostPatternEditor(
                        self.master,
                        [[x] for x in self.master.get_tcp_filter()],
                        self.master.edit_tcp_filter
                    )
                )
            elif k == "i":
                self.master.prompt(
                    "Intercept filter: ",
                    self.master.state.intercept_txt,
                    self.master.set_intercept
                )
            elif k == "Q":
                raise urwid.ExitMainLoop
            elif k == "q":
                self.master.prompt_onekey(
                    "Quit",
                    (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    self.master.quit,
                )
            elif k == "M":
                self.master.prompt_onekey(
                    "Global default display mode",
                    contentview.view_prompts,
                    self.master.change_default_display_mode
                )
            elif k == "R":
                self.master.view_grideditor(
                    grideditor.ReplaceEditor(
                        self.master,
                        self.master.replacehooks.get_specs(),
                        self.master.replacehooks.set
                    )
                )
            elif k == "s":
                self.master.view_grideditor(
                    grideditor.ScriptEditor(
                        self.master,
                        [[i.command] for i in self.master.scripts],
                        self.master.edit_scripts
                    )
                )
            elif k == "S":
                if not self.master.server_playback:
                    self.master.path_prompt(
                        "Server replay path: ",
                        self.master.state.last_saveload,
                        self.master.server_playback_path
                    )
                else:
                    self.master.prompt_onekey(
                        "Stop current server replay?",
                        (
                            ("yes", "y"),
                            ("no", "n"),
                        ),
                        self.master.stop_server_playback_prompt,
                    )
            elif k == "o":
                self.master.prompt_onekey(
                    "Options",
                    (
                        ("anticache", "a"),
                        ("anticomp", "c"),
                        ("showhost", "h"),
                        ("killextra", "k"),
                        ("norefresh", "n"),
                        ("no-upstream-certs", "u"),
                    ),
                    self.master._change_options
                )
            elif k == "t":
                self.master.prompt(
                    "Sticky cookie filter: ",
                    self.master.stickycookie_txt,
                    self.master.set_stickycookie
                )
            elif k == "u":
                self.master.prompt(
                    "Sticky auth filter: ",
                    self.master.stickyauth_txt,
                    self.master.set_stickyauth
                )
            else:
                return k
        self.footer.redraw()
