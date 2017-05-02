import urwid
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import statusbar
from mitmproxy.tools.console import flowlist
from mitmproxy.tools.console import flowview
from mitmproxy.tools.console import commands
from mitmproxy.tools.console import options
from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import help
from mitmproxy.tools.console import grideditor
from mitmproxy.tools.console import eventlog


class Window(urwid.Frame):
    def __init__(self, master):
        self.statusbar = statusbar.StatusBar(master, "")
        super().__init__(
            None,
            header = None,
            footer = urwid.AttrWrap(self.statusbar, "background")
        )
        self.master = master
        self.master.view.sig_view_refresh.connect(self.view_changed)
        self.master.view.sig_view_add.connect(self.view_changed)
        self.master.view.sig_view_remove.connect(self.view_changed)
        self.master.view.sig_view_update.connect(self.view_changed)
        self.master.view.focus.sig_change.connect(self.view_changed)
        signals.focus.connect(self.sig_focus)

        self.master.view.focus.sig_change.connect(self.focus_changed)
        signals.flow_change.connect(self.flow_changed)

        signals.pop_view_state.connect(self.pop)
        signals.push_view_state.connect(self.push)
        self.windows = dict(
            flowlist = flowlist.FlowListBox(self.master),
            flowview = flowview.FlowView(self.master),
            commands = commands.Commands(self.master),
            options = options.Options(self.master),
            help = help.HelpView(None),
            eventlog = eventlog.EventLog(self.master),

            edit_focus_query = grideditor.QueryEditor(self.master),
            edit_focus_cookies = grideditor.CookieEditor(self.master),
            edit_focus_setcookies = grideditor.SetCookieEditor(self.master),
            edit_focus_form = grideditor.RequestFormEditor(self.master),
            edit_focus_path = grideditor.PathEditor(self.master),
            edit_focus_request_headers = grideditor.RequestHeaderEditor(self.master),
            edit_focus_response_headers = grideditor.ResponseHeaderEditor(
                self.master
            ),
        )
        self.primary_stack = ["flowlist"]

    def refresh(self):
        self.body = urwid.AttrWrap(
            self.windows[self.primary_stack[-1]], "background"
        )

    def call(self, v, name, *args, **kwargs):
        f = getattr(v, name, None)
        if f:
            f(*args, **kwargs)

    def flow_changed(self, sender, flow):
        if self.master.view.focus.flow:
            if flow.id == self.master.view.focus.flow.id:
                self.focus_changed()

    def focus_changed(self, *args, **kwargs):
        """
            Triggered when the focus changes - either when it's modified, or
            when it changes to a different flow altogether.
        """
        self.call(self.focus, "focus_changed")

    def view_changed(self, *args, **kwargs):
        """
            Triggered when the view list has changed.
        """
        self.call(self.focus, "view_changed")

    def view_popping(self, *args, **kwargs):
        """
            Triggered when the view list has changed.
        """
        self.call(self.focus, "view_popping")

    def push(self, wname):
        if self.primary_stack and self.primary_stack[-1] == wname:
            return
        self.primary_stack.append(wname)
        self.refresh()
        self.view_changed()
        self.focus_changed()

    def pop(self, *args, **kwargs):
        if isinstance(self.master.loop.widget, overlay.SimpleOverlay):
            self.master.loop.widget = self
        else:
            if len(self.primary_stack) > 1:
                self.view_popping()
                self.primary_stack.pop()
                self.refresh()
                self.view_changed()
                self.focus_changed()
            else:
                self.master.prompt_for_exit()

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

    def keypress(self, size, k):
        if self.focus.keyctx:
            k = self.master.keymap.handle(self.focus.keyctx, k)
        if k:
            return super().keypress(size, k)
