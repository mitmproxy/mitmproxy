import csv
import typing

import mitmproxy.types
from mitmproxy import command, command_lexer
from mitmproxy import contentviews
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import log
from mitmproxy import tcp
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import signals
from mitmproxy.utils import strutils

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

console_flowlist_layout = [
    "default",
    "table",
    "list"
]


class UnsupportedLog:
    """
        A small addon to dump info on flow types we don't support yet.
    """

    def websocket_message(self, f):
        message = f.messages[-1]
        ctx.log.info(f.message_info(message))
        ctx.log.debug(
            message.content if isinstance(message.content, str) else strutils.bytes_to_escaped_str(message.content))

    def websocket_end(self, f):
        ctx.log.info("WebSocket connection closed by {}: {} {}, {}".format(
            f.close_sender,
            f.close_code,
            f.close_message,
            f.close_reason))

    def tcp_message(self, f):
        message = f.messages[-1]
        direction = "->" if message.from_client else "<-"
        ctx.log.info("{client_host}:{client_port} {direction} tcp {direction} {server_host}:{server_port}".format(
            client_host=f.client_conn.address[0],
            client_port=f.client_conn.address[1],
            server_host=f.server_conn.address[0],
            server_port=f.server_conn.address[1],
            direction=direction,
        ))
        ctx.log.debug(strutils.bytes_to_escaped_str(message.content))


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
            "console_default_contentview", str, "auto",
            "The default content view mode.",
            choices=[i.name.lower() for i in contentviews.views]
        )
        loader.add_option(
            "console_eventlog_verbosity", str, 'info',
            "EventLog verbosity.",
            choices=log.LogTierOrder
        )
        loader.add_option(
            "console_layout", str, "single",
            "Console layout.",
            choices=sorted(console_layouts),
        )
        loader.add_option(
            "console_layout_headers", bool, True,
            "Show layout component headers",
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
            "console_palette_transparent", bool, True,
            "Set transparent background for palette."
        )
        loader.add_option(
            "console_mouse", bool, True,
            "Console mouse interaction."
        )

        loader.add_option(
            "console_flowlist_layout",
            str, "default",
            "Set the flowlist layout",
            choices=sorted(console_flowlist_layout)
        )

    @command.command("console.layout.options")
    def layout_options(self) -> typing.Sequence[str]:
        """
            Returns the available options for the console_layout option.
        """
        return ["single", "vertical", "horizontal"]

    @command.command("console.layout.cycle")
    def layout_cycle(self) -> None:
        """
            Cycle through the console layout options.
        """
        opts = self.layout_options()
        off = self.layout_options().index(ctx.options.console_layout)
        ctx.options.update(
            console_layout=opts[(off + 1) % len(opts)]
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
        self.master.commands.call_strings("options.reset.one", [fv.current_name()])

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
            self,
            prompt: str,
            choices: typing.Sequence[str],
            cmd: mitmproxy.types.Cmd,
            *args: mitmproxy.types.CmdArgs
    ) -> None:
        """
            Prompt the user to choose from a specified list of strings, then
            invoke another command with all occurrences of {choice} replaced by
            the choice the user made.
        """

        def callback(opt):
            # We're now outside of the call context...
            repl = [arg.replace("{choice}", opt) for arg in args]
            try:
                self.master.commands.call_strings(cmd, repl)
            except exceptions.CommandError as e:
                ctx.log.error(str(e))

        self.master.overlay(
            overlay.Chooser(self.master, prompt, choices, "", callback)
        )

    @command.command("console.choose.cmd")
    def console_choose_cmd(
            self,
            prompt: str,
            choicecmd: mitmproxy.types.Cmd,
            subcmd: mitmproxy.types.Cmd,
            *args: mitmproxy.types.CmdArgs
    ) -> None:
        """
            Prompt the user to choose from a list of strings returned by a
            command, then invoke another command with all occurrences of {choice}
            replaced by the choice the user made.
        """
        choices = ctx.master.commands.execute(choicecmd)

        def callback(opt):
            # We're now outside of the call context...
            repl = [arg.replace("{choice}", opt) for arg in args]
            try:
                self.master.commands.call_strings(subcmd, repl)
            except exceptions.CommandError as e:
                ctx.log.error(str(e))

        self.master.overlay(
            overlay.Chooser(self.master, prompt, choices, "", callback)
        )

    @command.command("console.command")
    def console_command(self, *command_str: str) -> None:
        """
        Prompt the user to edit a command with a (possibly empty) starting value.
        """
        quoted = " ".join(command_lexer.quote(x) for x in command_str)
        if quoted:
            quoted += " "
        signals.status_prompt_command.send(partial=quoted)

    @command.command("console.command.set")
    def console_command_set(self, option_name: str) -> None:
        """
        Prompt the user to set an option.
        """
        option_value = getattr(self.master.options, option_name, None) or ""
        set_command = f"set {option_name} {option_value!r}"
        cursor = len(set_command) - 1
        signals.status_prompt_command.send(
            partial=set_command,
            cursor=cursor
        )

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
        if isinstance(flow, (http.HTTPFlow, tcp.TCPFlow)):
            self.master.switch_view("flowview")
        else:
            ctx.log.warn(f"No detail view for {type(flow).__name__}.")

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
    @command.argument("part", type=mitmproxy.types.Choice("console.bodyview.options"))
    def bodyview(self, flow: flow.Flow, part: str) -> None:
        """
            Spawn an external viewer for a flow request or response body based
            on the detected MIME type. We use the mailcap system to find the
            correct viewier, and fall back to the programs in $PAGER or $EDITOR
            if necessary.
        """
        fpart = getattr(flow, part, None)
        if not fpart:
            raise exceptions.CommandError("Part must be either request or response, not %s." % part)
        t = fpart.headers.get("content-type")
        content = fpart.get_content(strict=False)
        if not content:
            raise exceptions.CommandError("No content to view.")
        self.master.spawn_external_viewer(content, t)

    @command.command("console.bodyview.options")
    def bodyview_options(self) -> typing.Sequence[str]:
        """
            Possible parts for console.bodyview.
        """
        return ["request", "response"]

    @command.command("console.edit.focus.options")
    def edit_focus_options(self) -> typing.Sequence[str]:
        """
            Possible components for console.edit.focus.
        """
        return [
            "cookies",
            "urlencoded form",
            "multipart form",
            "path",
            "method",
            "query",
            "reason",
            "request-headers",
            "response-headers",
            "request-body",
            "response-body",
            "status_code",
            "set-cookies",
            "url",
        ]

    @command.command("console.edit.focus")
    @command.argument("flow_part", type=mitmproxy.types.Choice("console.edit.focus.options"))
    def edit_focus(self, flow_part: str) -> None:
        """
            Edit a component of the currently focused flow.
        """
        flow = self.master.view.focus.flow
        # This shouldn't be necessary once this command is "console.edit @focus",
        # but for now it is.
        if not flow:
            raise exceptions.CommandError("No flow selected.")
        flow.backup()

        require_dummy_response = (
                flow_part in ("response-headers", "response-body", "set-cookies") and
                flow.response is None
        )
        if require_dummy_response:
            flow.response = http.HTTPResponse.make()
        if flow_part == "cookies":
            self.master.switch_view("edit_focus_cookies")
        elif flow_part == "urlencoded form":
            self.master.switch_view("edit_focus_urlencoded_form")
        elif flow_part == "multipart form":
            self.master.switch_view("edit_focus_multipart_form")
        elif flow_part == "path":
            self.master.switch_view("edit_focus_path")
        elif flow_part == "query":
            self.master.switch_view("edit_focus_query")
        elif flow_part == "request-headers":
            self.master.switch_view("edit_focus_request_headers")
        elif flow_part == "response-headers":
            self.master.switch_view("edit_focus_response_headers")
        elif flow_part in ("request-body", "response-body"):
            if flow_part == "request-body":
                message = flow.request
            else:
                message = flow.response
            c = self.master.spawn_editor(message.get_content(strict=False) or b"")
            # Fix an issue caused by some editors when editing a
            # request/response body. Many editors make it hard to save a
            # file without a terminating newline on the last line. When
            # editing message bodies, this can cause problems. For now, I
            # just strip the newlines off the end of the body when we return
            # from an editor.
            message.content = c.rstrip(b"\n")
        elif flow_part == "set-cookies":
            self.master.switch_view("edit_focus_setcookies")
        elif flow_part == "url":
            url = flow.request.url.encode()
            edited_url = self.master.spawn_editor(url)
            url = edited_url.rstrip(b"\n")
            flow.request.url = url.decode()
        elif flow_part in ["method", "status_code", "reason"]:
            self.master.commands.call_strings(
                "console.command",
                ["flow.set", "@focus", flow_part]
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

    @command.command("console.grideditor.load")
    def grideditor_load(self, path: mitmproxy.types.Path) -> None:
        """
            Read a file into the currrent cell.
        """
        self._grideditor().cmd_read_file(path)

    @command.command("console.grideditor.load_escaped")
    def grideditor_load_escaped(self, path: mitmproxy.types.Path) -> None:
        """
            Read a file containing a Python-style escaped string into the
            currrent cell.
        """
        self._grideditor().cmd_read_file_escaped(path)

    @command.command("console.grideditor.save")
    def grideditor_save(self, path: mitmproxy.types.Path) -> None:
        """
            Save data to file as a CSV.
        """
        rows = self._grideditor().value
        try:
            with open(path, "w", newline='', encoding="utf8") as fp:
                writer = csv.writer(fp)
                for row in rows:
                    writer.writerow(
                        [strutils.always_str(x) or "" for x in row]  # type: ignore
                    )
            ctx.log.alert("Saved %s rows as CSV." % (len(rows)))
        except IOError as e:
            ctx.log.error(str(e))

    @command.command("console.grideditor.editor")
    def grideditor_editor(self) -> None:
        """
            Spawn an external editor on the current cell.
        """
        self._grideditor().cmd_spawn_editor()

    @command.command("console.flowview.mode.set")
    @command.argument("mode", type=mitmproxy.types.Choice("console.flowview.mode.options"))
    def flowview_mode_set(self, mode: str) -> None:
        """
            Set the display mode for the current flow view.
        """
        fv = self.master.window.current_window("flowview")
        if not fv:
            raise exceptions.CommandError("Not viewing a flow.")
        idx = fv.body.tab_offset

        if mode not in [i.name.lower() for i in contentviews.views]:
            raise exceptions.CommandError("Invalid flowview mode.")

        try:
            self.master.commands.call_strings(
                "view.settings.setval",
                ["@focus", "flowview_mode_%s" % (idx,), mode]
            )
        except exceptions.CommandError as e:
            ctx.log.error(str(e))

    @command.command("console.flowview.mode.options")
    def flowview_mode_options(self) -> typing.Sequence[str]:
        """
            Returns the valid options for the flowview mode.
        """
        return [i.name.lower() for i in contentviews.views]

    @command.command("console.flowview.mode")
    def flowview_mode(self) -> str:
        """
            Get the display mode for the current flow view.
        """
        fv = self.master.window.current_window("flowview")
        if not fv:
            raise exceptions.CommandError("Not viewing a flow.")
        idx = fv.body.tab_offset

        return self.master.commands.call_strings(
            "view.settings.getval",
            ["@focus", "flowview_mode_%s" % (idx,), self.master.options.console_default_contentview]
        )

    @command.command("console.key.contexts")
    def key_contexts(self) -> typing.Sequence[str]:
        """
            The available contexts for key binding.
        """
        return list(sorted(keymap.Contexts))

    @command.command("console.key.bind")
    def key_bind(
            self,
            contexts: typing.Sequence[str],
            key: str,
            cmd: mitmproxy.types.Cmd,
            *args: mitmproxy.types.CmdArgs
    ) -> None:
        """
            Bind a shortcut key.
        """
        try:
            self.master.keymap.add(
                key,
                cmd + " " + " ".join(args),
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
        f = kwidget.get_focused_binding()
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
