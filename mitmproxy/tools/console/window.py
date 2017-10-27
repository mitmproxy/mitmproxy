import re

import urwid
from mitmproxy.tools.console import common
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import statusbar
from mitmproxy.tools.console import flowlist
from mitmproxy.tools.console import flowview
from mitmproxy.tools.console import commands
from mitmproxy.tools.console import keybindings
from mitmproxy.tools.console import options
from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import help
from mitmproxy.tools.console import grideditor
from mitmproxy.tools.console import eventlog


class Header(urwid.Frame):
    def __init__(self, widget, title, focus):
        super().__init__(
            widget,
            header = urwid.AttrWrap(
                urwid.Text(title),
                "heading" if focus else "heading_inactive"
            )
        )


class WindowStack:
    def __init__(self, master, base):
        self.master = master
        self.windows = dict(
            flowlist = flowlist.FlowListBox(master),
            flowview = flowview.FlowView(master),
            commands = commands.Commands(master),
            keybindings = keybindings.KeyBindings(master),
            options = options.Options(master),
            help = help.HelpView(master),
            eventlog = eventlog.EventLog(master),

            edit_focus_query = grideditor.QueryEditor(master),
            edit_focus_cookies = grideditor.CookieEditor(master),
            edit_focus_setcookies = grideditor.SetCookieEditor(master),
            edit_focus_form = grideditor.RequestFormEditor(master),
            edit_focus_path = grideditor.PathEditor(master),
            edit_focus_request_headers = grideditor.RequestHeaderEditor(master),
            edit_focus_response_headers = grideditor.ResponseHeaderEditor(master),
        )
        self.stack = [base]
        self.overlay = None

    def set_overlay(self, o, **kwargs):
        self.overlay = overlay.SimpleOverlay(
            self, o, self.top_widget(), o.width, **kwargs,
        )

    def top_window(self):
        """
            The current top window, ignoring overlays.
        """
        return self.windows[self.stack[-1]]

    def top_widget(self):
        """
            The current top widget - either a window or the active overlay.
        """
        if self.overlay:
            return self.overlay
        return self.top_window()

    def push(self, wname):
        if self.stack[-1] == wname:
            return
        prev = self.top_window()
        self.stack.append(wname)
        self.call("layout_pushed", prev)

    def pop(self, *args, **kwargs):
        """
            Pop off the stack, return True if we're already at the top.
        """
        if not self.overlay and len(self.stack) == 1:
            return True
        self.call("layout_popping")
        if self.overlay:
            self.overlay = None
        else:
            self.stack.pop()

    def call(self, name, *args, **kwargs):
        """
            Call a function on both the top window, and the overlay if there is
            one. If the widget has a key_responder, we call the function on the
            responder instead.
        """
        getattr(self.top_window(), name)(*args, **kwargs)
        if self.overlay:
            getattr(self.overlay, name)(*args, **kwargs)


class Window(urwid.Frame):
    def __init__(self, master):
        self.statusbar = statusbar.StatusBar(master)
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
        self.master.view.focus.sig_change.connect(self.focus_changed)

        signals.focus.connect(self.sig_focus)
        signals.flow_change.connect(self.flow_changed)
        signals.pop_view_state.connect(self.pop)
        signals.push_view_state.connect(self.push)

        self.master.options.subscribe(self.configure, ["console_layout"])
        self.master.options.subscribe(self.configure, ["console_layout_headers"])
        self.pane = 0
        self.stacks = [
            WindowStack(master, "flowlist"),
            WindowStack(master, "eventlog")
        ]

    def focus_stack(self):
        return self.stacks[self.pane]

    def configure(self, otions, updated):
        self.refresh()

    def refresh(self):
        """
            Redraw the layout.
        """
        c = self.master.options.console_layout
        if c == "single":
            self.pane = 0

        def wrapped(idx):
            window = self.stacks[idx].top_window()
            widget = self.stacks[idx].top_widget()
            if self.master.options.console_layout_headers and window.title:
                return Header(widget, window.title, self.pane == idx)
            else:
                return widget

        w = None
        if c == "single":
            w = wrapped(0)
        elif c == "vertical":
            w = urwid.Pile(
                [
                    wrapped(i) for i, s in enumerate(self.stacks)
                ]
            )
        else:
            w = urwid.Columns(
                [wrapped(i) for i, s in enumerate(self.stacks)],
                dividechars=1
            )

        self.body = urwid.AttrWrap(w, "background")

    def flow_changed(self, sender, flow):
        if self.master.view.focus.flow:
            if flow.id == self.master.view.focus.flow.id:
                self.focus_changed()

    def focus_changed(self, *args, **kwargs):
        """
            Triggered when the focus changes - either when it's modified, or
            when it changes to a different flow altogether.
        """
        for i in self.stacks:
            i.call("focus_changed")

    def view_changed(self, *args, **kwargs):
        """
            Triggered when the view list has changed.
        """
        for i in self.stacks:
            i.call("view_changed")

    def set_overlay(self, o, **kwargs):
        """
            Set an overlay on the currently focused stack.
        """
        self.focus_stack().set_overlay(o, **kwargs)
        self.refresh()

    def push(self, wname):
        """
            Push a window onto the currently focused stack.
        """
        self.focus_stack().push(wname)
        self.refresh()
        self.view_changed()
        self.focus_changed()

    def pop(self, *args, **kwargs):
        """
            Pop a window from the currently focused stack. If there is only one
            window on the stack, this prompts for exit.
        """
        if self.focus_stack().pop():
            self.master.prompt_for_exit()
        else:
            self.refresh()
            self.view_changed()
            self.focus_changed()

    def current(self, keyctx):
        """
            Returns the active widget, but only the current focus or overlay has
            a matching key context.
        """
        t = self.focus_stack().top_widget()
        if t.keyctx == keyctx:
            return t

    def current_window(self, keyctx):
        """
            Returns the active window, ignoring overlays.
        """
        t = self.focus_stack().top_window()
        if t.keyctx == keyctx:
            return t

    def any(self, keyctx):
        """
            Returns the top window of either stack if they match the context.
        """
        for t in [x.top_window() for x in self.stacks]:
            if t.keyctx == keyctx:
                return t

    def sig_focus(self, sender, section):
        self.focus_position = section

    def switch(self):
        """
            Switch between the two panes.
        """
        if self.master.options.console_layout == "single":
            self.pane = 0
        else:
            self.pane = (self.pane + 1) % len(self.stacks)
        self.refresh()

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
        if self.focus_part == "footer":
            return super().keypress(size, k)
        else:
            fs = self.focus_stack().top_widget()
            k = fs.keypress(size, k)
            if k:
                return self.master.keymap.handle(fs.keyctx, k)


class Screen(urwid.raw_display.Screen):

    def write(self, data):
        if common.IS_WSL:
            # replace urwid's SI/SO, which produce artifacts under WSL.
            # at some point we may figure out what they actually do.
            data = re.sub("[\x0e\x0f]", "", data)
        super().write(data)
