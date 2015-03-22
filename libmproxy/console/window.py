import urwid
from . import common, grideditor, signals, contentview

class Window(urwid.Frame):
    def __init__(self, master, body, header, footer):
        urwid.Frame.__init__(self, body, header=header, footer=footer)
        self.master = master
        signals.focus.connect(self.sig_focus)

    def sig_focus(self, sender, section):
        self.focus_position = section

    def keypress(self, size, k):
        k = urwid.Frame.keypress(self, self.master.loop.screen_size, k)
        if k == "?":
            self.master.view_help()
        elif k == "c":
            if not self.master.client_playback:
                signals.status_prompt_path.send(
                    self,
                    prompt = "Client replay",
                    callback = self.master.client_playback_path
                )
            else:
                signals.status_prompt_onekey.send(
                    self,
                    prompt = "Stop current client replay?",
                    keys = (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    callback = self.master.stop_client_playback_prompt,
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
            signals.status_prompt.send(
                self,
                prompt = "Intercept filter",
                text = self.master.state.intercept_txt,
                callback = self.master.set_intercept
            )
        elif k == "Q":
            raise urwid.ExitMainLoop
        elif k == "q":
            signals.status_prompt_onekey.send(
                self,
                prompt = "Quit",
                keys = (
                    ("yes", "y"),
                    ("no", "n"),
                ),
                callback = self.master.quit,
            )
        elif k == "M":
            signals.status_prompt_onekey.send(
                prompt = "Global default display mode",
                keys = contentview.view_prompts,
                callback = self.master.change_default_display_mode
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
                signals.status_prompt_path.send(
                    self,
                    prompt = "Server replay path",
                    callback = self.master.server_playback_path
                )
            else:
                signals.status_prompt_onekey.send(
                    self,
                    prompt = "Stop current server replay?",
                    keys = (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    callback = self.master.stop_server_playback_prompt,
                )
        elif k == "o":
            signals.status_prompt_onekey.send(
                prompt = "Options",
                keys = (
                    ("anticache", "a"),
                    ("anticomp", "c"),
                    ("showhost", "h"),
                    ("killextra", "k"),
                    ("norefresh", "n"),
                    ("no-upstream-certs", "u"),
                ),
                callback = self.master._change_options
            )
        elif k == "t":
            signals.status_prompt.send(
                prompt = "Sticky cookie filter",
                text = self.master.stickycookie_txt,
                callback = self.master.set_stickycookie
            )
        elif k == "u":
            signals.status_prompt.send(
                prompt = "Sticky auth filter",
                text = self.master.stickyauth_txt,
                callback = self.master.set_stickyauth
            )
        else:
            return k
