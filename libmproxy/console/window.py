import urwid
from . import grideditor, signals, contentview


class Window(urwid.Frame):
    def __init__(self, master, body, header, footer, helpctx):
        urwid.Frame.__init__(self, body, header=header, footer=footer)
        self.master = master
        self.helpctx = helpctx
        signals.focus.connect(self.sig_focus)

    def sig_focus(self, sender, section):
        self.focus_position = section

    def keypress(self, size, k):
        k = super(self.__class__, self).keypress(size, k)
        if k == "?":
            self.master.view_help(self.helpctx)
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
        elif k == "i":
            signals.status_prompt.send(
                self,
                prompt = "Intercept filter",
                text = self.master.state.intercept_txt,
                callback = self.master.set_intercept
            )
        elif k == "o":
            self.master.view_options()
        elif k == "Q":
            raise urwid.ExitMainLoop
        elif k == "q":
            signals.pop_view_state.send(self)
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
        else:
            return k
