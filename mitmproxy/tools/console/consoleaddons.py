import typing

from mitmproxy import ctx
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import contentviews
from mitmproxy.utils import strutils

from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import keymap

console_palettes = [
    "lowlight",
    "lowdark",
    "light",
    "dark",
    "solarized_light",
    "solarized_dark"
]
view_orders = [
    "time",
    "method",
    "url",
    "size",
]
console_layouts = [
    "single",
    "vertical",
    "horizontal",
]


class Logger:
    def log(self, evt):
        signals.add_log(evt.msg, evt.level)
        if evt.level == "alert":
            signals.status_message.send(
                message=str(evt.msg),
                expire=2
            )


class UnsupportedLog:
    """
        A small addon to dump info on flow types we don't support yet.
    """
    def websocket_message(self, f):
        message = f.messages[-1]
        signals.add_log(f.message_info(message), "info")
        signals.add_log(strutils.bytes_to_escaped_str(message.content), "debug")

    def websocket_end(self, f):
        signals.add_log("WebSocket connection closed by {}: {} {}, {}".format(
            f.close_sender,
            f.close_code,
            f.close_message,
            f.close_reason), "info")

    def tcp_message(self, f):
        message = f.messages[-1]
        direction = "->" if message.from_client else "<-"
        signals.add_log("{client_host}:{client_port} {direction} tcp {direction} {server_host}:{server_port}".format(
            client_host=f.client_conn.address[0],
            client_port=f.client_conn.address[1],
            server_host=f.server_conn.address[0],
            server_port=f.server_conn.address[1],
            direction=direction,
        ), "info")
        signals.add_log(strutils.bytes_to_escaped_str(message.content), "debug")


class ConsoleAddon:
    """
        An addon that exposes console-specific commands, and hooks into required
        events.
    """
    def __init__(self, master):
        self.master = master
        self.started = False

    def load(self, loader):
        loader.add_option(
            "console_layout", str, "single",
            "Console layout.",
            choices=sorted(console_layouts),
        )
        loader.add_option(
            "console_layout_headers", bool, True,
            "Show layout comonent headers",
        )
        loader.add_option(
            "console_focus_follow", bool, False,
            "Focus follows new flows."
        )
        loader.add_option(
            "console_palette", str, "solarized_dark",
            "Color palette.",
            choices=sorted(console_palettes),
        )
        loader.add_option(
            "console_palette_transparent", bool, False,
            "Set transparent background for palette."
        )
        loader.add_option(
            "console_mouse", bool, True,
            "Console mouse interaction."
        )

    @command.command("console.layout.options")
    def layout_options(self) -> typing.Sequence[str]:
        """
            Returns the valid options for console layout. Use these by setting
            the console_layout option.
        """
        return ["single", "vertical", "horizontal"]

    @command.command("intercept_toggle")
    def intercept_toggle(self) -> None:
        """
            Toggles interception on/off leaving intercept filters intact.
        """
        ctx.options.intercept_active = not ctx.options.intercept_active

    @command.command("console.layout.cycle")
    def layout_cycle(self) -> None:
        """
            Cycle through the console layout options.
        """
        opts = self.layout_options()
        off = self.layout_options().index(ctx.options.console_layout)
        ctx.options.update(
            console_layout = opts[(off + 1) % len(opts)]
        )

    @command.command("console.panes.next")
    def panes_next(self) -> None:
        """
            Go to the next layout pane.
        """
        self.master.window.switch()

    @command.command("console.options.reset.focus")
    def options_reset_current(self) -> None:
        """
            Reset the current option in the options editor.
        """
        fv = self.master.window.current("options")
        if not fv:
            raise exceptions.CommandError("Not viewing options.")
        self.master.commands.call("options.reset.one %s" % fv.current_name())

    @command.command("console.nav.start")
    def nav_start(self) -> None:
        """
            Go to the start of a list or scrollable.
        """
        self.master.inject_key("m_start")

    @command.command("console.nav.end")
    def nav_end(self) -> None:
        """
            Go to the end of a list or scrollable.
        """
        self.master.inject_key("m_end")

    @command.command("console.nav.next")
    def nav_next(self) -> None:
        """
            Go to the next navigatable item.
        """
        self.master.inject_key("m_next")

    @command.command("console.nav.select")
    def nav_select(self) -> None:
        """
            Select a navigable item for viewing or editing.
        """
        self.master.inject_key("m_select")

    @command.command("console.nav.up")
    def nav_up(self) -> None:
        """
            Go up.
        """
        self.master.inject_key("up")

    @command.command("console.nav.down")
    def nav_down(self) -> None:
        """
            Go down.
        """
        self.master.inject_key("down")

    @command.command("console.nav.pageup")
    def nav_pageup(self) -> None:
        """
            Go up.
        """
        self.master.inject_key("page up")

    @command.command("console.nav.pagedown")
    def nav_pagedown(self) -> None:
        """
            Go down.
        """
        self.master.inject_key("page down")

    @command.command("console.nav.left")
    def nav_left(self) -> None:
        """
            Go left.
        """
        self.master.inject_key("left")

    @command.command("console.nav.right")
    def nav_right(self) -> None:
        """
            Go right.
        """
        self.master.inject_key("right")

    @command.command("console.choose")
    def console_choose(
        self, prompt: str, choices: typing.Sequence[str], *cmd: str
    ) -> None:
        """
            Prompt the user to choose from a specified list of strings, then
            invoke another command with all occurances of {choice} replaced by
            the choice the user made.
        """
        def callback(opt):
            # We're now outside of the call context...
            repl = " ".join(cmd)
            repl = repl.replace("{choice}", opt)
            try:
                self.master.commands.call(repl)
            except exceptions.CommandError as e:
                signals.status_message.send(message=str(e))

        self.master.overlay(
            overlay.Chooser(self.master, prompt, choices, "", callback)
        )

    @command.command("console.choose.cmd")
    def console_choose_cmd(
        self, prompt: str, choicecmd: str, *cmd: str
    ) -> None:
        """
            Prompt the user to choose from a list of strings returned by a
            command, then invoke another command with all occurances of {choice}
            replaced by the choice the user made.
        """
        choices = ctx.master.commands.call_args(choicecmd, [])

        def callback(opt):
            # We're now outside of the call context...
            repl = " ".join(cmd)
            repl = repl.replace("{choice}", opt)
            try:
                self.master.commands.call(repl)
            except exceptions.CommandError as e:
                signals.status_message.send(message=str(e))

        self.master.overlay(
            overlay.Chooser(self.master, prompt, choices, "", callback)
        )

    @command.command("console.command")
    def console_command(self, *partial: str) -> None:
        """
        Prompt the user to edit a command with a (possilby empty) starting value.
        """
        signals.status_prompt_command.send(partial=" ".join(partial))  # type: ignore

    @command.command("console.view.keybindings")
    def view_keybindings(self) -> None:
        """View the commands list."""
        self.master.switch_view("keybindings")

    @command.command("console.view.commands")
    def view_commands(self) -> None:
        """View the commands list."""
        self.master.switch_view("commands")

    @command.command("console.view.options")
    def view_options(self) -> None:
        """View the options editor."""
        self.master.switch_view("options")

    @command.command("console.view.eventlog")
    def view_eventlog(self) -> None:
        """View the options editor."""
        self.master.switch_view("eventlog")

    @command.command("console.view.help")
    def view_help(self) -> None:
        """View help."""
        self.master.switch_view("help")

    @command.command("console.view.flow")
    def view_flow(self, flow: flow.Flow) -> None:
        """View a flow."""
        if hasattr(flow, "request"):
            # FIME: Also set focus?
            self.master.switch_view("flowview")

    @command.command("console.exit")
    def exit(self) -> None:
        """Exit mitmproxy."""
        self.master.shutdown()

    @command.command("console.view.pop")
    def view_pop(self) -> None:
        """
            Pop a view off the console stack. At the top level, this prompts the
            user to exit mitmproxy.
        """
        signals.pop_view_state.send(self)

    @command.command("console.bodyview")
    def bodyview(self, f: flow.Flow, part: str) -> None:
        """
            Spawn an external viewer for a flow request or response body based
            on the detected MIME type. We use the mailcap system to find the
            correct viewier, and fall back to the programs in $PAGER or $EDITOR
            if necessary.
        """
        fpart = getattr(f, part)
        if not fpart:
            raise exceptions.CommandError("Could not view part %s." % part)
        t = fpart.headers.get("content-type")
        content = fpart.get_content(strict=False)
        if not content:
            raise exceptions.CommandError("No content to view.")
        self.master.spawn_external_viewer(content, t)

    @command.command("console.edit.focus.options")
    def edit_focus_options(self) -> typing.Sequence[str]:
        return [
            "cookies",
            "form",
            "path",
            "method",
            "query",
            "reason",
            "request-headers",
            "response-headers",
            "status_code",
            "set-cookies",
            "url",
        ]

    @command.command("console.edit.focus")
    def edit_focus(self, part: str) -> None:
        """
            Edit the query of the current focus.
        """
        if part == "cookies":
            self.master.switch_view("edit_focus_cookies")
        elif part == "form":
            self.master.switch_view("edit_focus_form")
        elif part == "path":
            self.master.switch_view("edit_focus_path")
        elif part == "query":
            self.master.switch_view("edit_focus_query")
        elif part == "request-headers":
            self.master.switch_view("edit_focus_request_headers")
        elif part == "response-headers":
            self.master.switch_view("edit_focus_response_headers")
        elif part == "set-cookies":
            self.master.switch_view("edit_focus_setcookies")
        elif part in ["url", "method", "status_code", "reason"]:
            self.master.commands.call(
                "console.command flow.set @focus %s " % part
            )

    def _grideditor(self):
        gewidget = self.master.window.current("grideditor")
        if not gewidget:
            raise exceptions.CommandError("Not in a grideditor.")
        return gewidget.key_responder()

    @command.command("console.grideditor.add")
    def grideditor_add(self) -> None:
        """
            Add a row after the cursor.
        """
        self._grideditor().cmd_add()

    @command.command("console.grideditor.insert")
    def grideditor_insert(self) -> None:
        """
            Insert a row before the cursor.
        """
        self._grideditor().cmd_insert()

    @command.command("console.grideditor.delete")
    def grideditor_delete(self) -> None:
        """
            Delete row
        """
        self._grideditor().cmd_delete()

    @command.command("console.grideditor.readfile")
    def grideditor_readfile(self, path: str) -> None:
        """
            Read a file into the currrent cell.
        """
        self._grideditor().cmd_read_file(path)

    @command.command("console.grideditor.readfile_escaped")
    def grideditor_readfile_escaped(self, path: str) -> None:
        """
            Read a file containing a Python-style escaped stringinto the
            currrent cell.
        """
        self._grideditor().cmd_read_file_escaped(path)

    @command.command("console.grideditor.editor")
    def grideditor_editor(self) -> None:
        """
            Spawn an external editor on the current cell.
        """
        self._grideditor().cmd_spawn_editor()

    @command.command("console.flowview.mode.set")
    def flowview_mode_set(self) -> None:
        """
            Set the display mode for the current flow view.
        """
        fv = self.master.window.current("flowview")
        if not fv:
            raise exceptions.CommandError("Not viewing a flow.")
        idx = fv.body.tab_offset

        def callback(opt):
            try:
                self.master.commands.call_args(
                    "view.setval",
                    ["@focus", "flowview_mode_%s" % idx, opt]
                )
            except exceptions.CommandError as e:
                signals.status_message.send(message=str(e))

        opts = [i.name.lower() for i in contentviews.views]
        self.master.overlay(overlay.Chooser(self.master, "Mode", opts, "", callback))

    @command.command("console.flowview.mode")
    def flowview_mode(self) -> str:
        """
            Get the display mode for the current flow view.
        """
        fv = self.master.window.current_window("flowview")
        if not fv:
            raise exceptions.CommandError("Not viewing a flow.")
        idx = fv.body.tab_offset
        return self.master.commands.call_args(
            "view.getval",
            [
                "@focus",
                "flowview_mode_%s" % idx,
                self.master.options.default_contentview,
            ]
        )

    @command.command("console.eventlog.clear")
    def eventlog_clear(self) -> None:
        """
            Clear the event log.
        """
        signals.sig_clear_log.send(self)

    @command.command("console.key.contexts")
    def key_contexts(self) -> typing.Sequence[str]:
        """
            The available contexts for key binding.
        """
        return list(sorted(keymap.Contexts))

    @command.command("console.key.bind")
    def key_bind(self, contexts: typing.Sequence[str], key: str, *command: str) -> None:
        """
            Bind a shortcut key.
        """
        try:
            self.master.keymap.add(
                key,
                " ".join(command),
                contexts,
                ""
            )
        except ValueError as v:
            raise exceptions.CommandError(v)

    @command.command("console.key.unbind")
    def key_unbind(self, contexts: typing.Sequence[str], key: str) -> None:
        """
            Un-bind a shortcut key.
        """
        try:
            self.master.keymap.remove(key, contexts)
        except ValueError as v:
            raise exceptions.CommandError(v)

    def _keyfocus(self):
        kwidget = self.master.window.current("keybindings")
        if not kwidget:
            raise exceptions.CommandError("Not viewing key bindings.")
        f = kwidget.focus()
        if not f:
            raise exceptions.CommandError("No key binding focused")
        return f

    @command.command("console.key.unbind.focus")
    def key_unbind_focus(self) -> None:
        """
            Un-bind the shortcut key currently focused in the key binding viewer.
        """
        b = self._keyfocus()
        try:
            self.master.keymap.remove(b.key, b.contexts)
        except ValueError as v:
            raise exceptions.CommandError(v)

    @command.command("console.key.execute.focus")
    def key_execute_focus(self) -> None:
        """
            Execute the currently focused key binding.
        """
        b = self._keyfocus()
        self.console_command(b.command)

    @command.command("console.key.edit.focus")
    def key_edit_focus(self) -> None:
        """
            Execute the currently focused key binding.
        """
        b = self._keyfocus()
        self.console_command(
            "console.key.bind",
            ",".join(b.contexts),
            b.key,
            b.command,
        )

    def running(self):
        self.started = True

    def update(self, flows):
        if not flows:
            signals.update_settings.send(self)
        for f in flows:
            signals.flow_change.send(self, flow=f)
