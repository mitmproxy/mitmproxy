import urwid

from mitmproxy.tools.console import signals


class Window(urwid.Frame):

    def __init__(self, master, body, header, footer, helpctx):
        urwid.Frame.__init__(
            self,
            urwid.AttrWrap(body, "background"),
            header = urwid.AttrWrap(header, "background") if header else None,
            footer = urwid.AttrWrap(footer, "background") if footer else None
        )
        self.master = master
        self.helpctx = helpctx
        signals.focus.connect(self.sig_focus)

    def sig_focus(self, sender, section):
        self.focus_position = section

    def mouse_event(self, *args, **kwargs):
        # args: (size, event, button, col, row)
        k = super().mouse_event(*args, **kwargs)
        if not k:
            if args[1] == "mouse drag":
                signals.status_message.send(
                    message = "Hold down fn, shift, alt or ctrl to select text or use the --no-mouse parameter.",
                    expire = 1
                )
            elif args[1] == "mouse press" and args[2] == 4:
                self.keypress(args[0], "up")
            elif args[1] == "mouse press" and args[2] == 5:
                self.keypress(args[0], "down")
            else:
                return False
            return True

    def handle_replay(self, k):
        if k == "c":
            creplay = self.master.addons.get("clientplayback")
            if self.master.options.client_replay and creplay.count():
                def stop_client_playback_prompt(a):
                    if a != "n":
                        self.master.options.client_replay = None
                signals.status_prompt_onekey.send(
                    self,
                    prompt = "Stop current client replay?",
                    keys = (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    callback = stop_client_playback_prompt
                )
            else:
                signals.status_prompt_path.send(
                    self,
                    prompt = "Client replay path",
                    callback = lambda x: self.master.options.setter("client_replay")([x])
                )
        elif k == "s":
            a = self.master.addons.get("serverplayback")
            if a.count():
                def stop_server_playback(response):
                    if response == "y":
                        self.master.options.server_replay = []
                signals.status_prompt_onekey.send(
                    self,
                    prompt = "Stop current server replay?",
                    keys = (
                        ("yes", "y"),
                        ("no", "n"),
                    ),
                    callback = stop_server_playback
                )
            else:
                signals.status_prompt_path.send(
                    self,
                    prompt = "Server playback path",
                    callback = lambda x: self.master.options.setter("server_replay")([x])
                )

    def keypress(self, size, k):
        k = super().keypress(size, k)
        if k == "?":
            self.master.view_help(self.helpctx)
        elif k == "i":
            signals.status_prompt.send(
                self,
                prompt = "Intercept filter",
                text = self.master.options.intercept,
                callback = self.master.options.setter("intercept")
            )
        elif k == "O":
            self.master.view_options()
        elif k == "Q":
            raise urwid.ExitMainLoop
        elif k == "q":
            signals.pop_view_state.send(self)
        elif k == "R":
            signals.status_prompt_onekey.send(
                self,
                prompt = "Replay",
                keys = (
                    ("client", "c"),
                    ("server", "s"),
                ),
                callback = self.handle_replay,
            )
        else:
            return k
