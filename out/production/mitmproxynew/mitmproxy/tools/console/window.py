import os
import re

import urwid
from mitmproxy.tools.console import commands
from mitmproxy.tools.console import common
from mitmproxy.tools.console import eventlog
from mitmproxy.tools.console import flowlist
from mitmproxy.tools.console import flowview
from mitmproxy.tools.console import grideditor
from mitmproxy.tools.console import help
from mitmproxy.tools.console import keybindings
from mitmproxy.tools.console import options
from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import statusbar

if os.name == "nt":
    from mitmproxy.contrib.urwid import raw_display
else:
    from urwid import raw_display  # type: ignore


class StackWidget(urwid.Frame):
    def __init__(self, window, widget, title, focus):
        self.is_focused = focus
        self.window = window

        if title:
            header = urwid.AttrWrap(
                urwid.Text(title),
                "heading" if focus else "heading_inactive"
            )
        else:
            header = None
        super().__init__(
            widget,
            header=header
        )

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1 and not self.is_focused:
            self.window.switch()
        return super().mouse_event(size, event, button, col, row, focus)

    def keypress(self, size, key):
        # Make sure that we don't propagate cursor events outside of the widget.
        # Otherwise, in a horizontal layout, urwid's Pile would change the focused widget
        # if we cannot scroll any further.
        ret = super().keypress(size, key)
        command = self._command_map[ret]  # awkward as they don't implement a full dict api
        if command and command.startswith("cursor"):
            return None
        return ret


class WindowStack:
    def __init__(self, master, base):
        self.master = master
        self.windows = dict(
            flowlist=flowlist.FlowListBox(master),
            flowview=flowview.FlowView(master),
            commands=commands.Commands(master),
            keybindings=keybindings.KeyBindings(master),
            options=options.Options(master),
            help=help.HelpView(master),
            eventlog=eventlog.EventLog(master),

            edit_focus_query=grideditor.QueryEditor(master),
            edit_focus_cookies=grideditor.CookieEditor(master),
            edit_focus_setcookies=grideditor.SetCookieEditor(master),
            edit_focus_setcookie_attrs=grideditor.CookieAttributeEditor(master),
            edit_focus_multipart_form=grideditor.RequestMultipartEditor(master),
            edit_focus_urlencoded_form=grideditor.RequestUrlEncodedEditor(master),
            edit_focus_path=grideditor.PathEditor(master),
            edit_focus_request_headers=grideditor.RequestHeaderEditor(master),
            edit_focus_response_headers=grideditor.ResponseHeaderEditor(master),
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
            header=None,
            footer=urwid.AttrWrap(self.statusbar, "background")
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
            widget = self.stacks[idx].top_widget()
            if self.master.options.console_layout_headers:
                title = self.stacks[idx].top_window().title
            else:
                title = None
            return StackWidget(
                self,
                widget,
                title,
                self.pane == idx
            )

        w = None
        if c == "single":
            w = wrapped(0)
        elif c == "vertical":
            w = urwid.Pile(
                [
                    wrapped(i) for i, s in enumerate(self.stacks)
                ],
                focus_item=self.pane
            )
        else:
            w = urwid.Columns(
                [wrapped(i) for i, s in enumerate(self.stacks)],
                dividechars=1,
                focus_column=self.pane
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

    def stacks_sorted_by_focus(self):
        """
        Returns:
            self.stacks, with the focused stack first.
        """
        stacks = self.stacks.copy()
        stacks.insert(0, stacks.pop(self.pane))
        return stacks

    def current(self, keyctx):
        """
        Returns the active widget with a matching key context, including overlays.
        If multiple stacks have an active widget with a matching key context,
        the currently focused stack is preferred.
        """
        for s in self.stacks_sorted_by_focus():
            t = s.top_widget()
            if t.keyctx == keyctx:
                return t

    def current_window(self, keyctx):
        """
        Returns the active window with a matching key context, ignoring overlays.
        If multiple stacks have an active widget with a matching key context,
        the currently focused stack is preferred.
        """
        for s in self.stacks_sorted_by_focus():
            t = s.top_window()
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
                    message="Hold down fn, shift, alt or ctrl to select text or use the --set console_mouse=false parameter.",
                    expire=1
                )
            elif args[1] == "mouse press" and args[2] == 4:
                self.keypress(args[0], "up")
            elif args[1] == "mouse press" and args[2] == 5:
                self.keypress(args[0], "down")
            else:
                return False
            return True

    def keypress(self, size, k):
        k = super().keypress(size, k)
        if k:
            return self.master.keymap.handle(
                self.focus_stack().top_widget().keyctx,
                k
            )


class Screen(raw_display.Screen):

    def write(self, data):
        if common.IS_WINDOWS:
            # replace urwid's SI/SO, which produce artifacts under WSL.
            # at some point we may figure out what they actually do.
            data = re.sub("[\x0e\x0f]", "", data)
        super().write(data)
