import mailcap
import mimetypes
import os
import os.path
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
import traceback

import urwid

from mitmproxy import addons
from mitmproxy import exceptions
from mitmproxy import command
from mitmproxy import master
from mitmproxy import io
from mitmproxy import log
from mitmproxy import flow
from mitmproxy.addons import intercept
from mitmproxy.addons import readfile
from mitmproxy.addons import view
from mitmproxy.tools.console import flowlist
from mitmproxy.tools.console import flowview
from mitmproxy.tools.console import grideditor
from mitmproxy.tools.console import help
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import options
from mitmproxy.tools.console import commands
from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import palettes
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import statusbar
from mitmproxy.tools.console import window
from mitmproxy.utils import strutils

EVENTLOG_SIZE = 10000


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
        An addon that exposes console-specific commands.
    """
    def __init__(self, master):
        self.master = master
        self.started = False

    @command.command("console.command")
    def console_command(self, partial: str) -> None:
        """
        Prompt the user to edit a command with a (possilby empty) starting value.
        """
        signals.status_prompt_command.send(partial=partial)

    @command.command("console.view.commands")
    def view_commands(self) -> None:
        """View the commands list."""
        self.master.view_commands()

    @command.command("console.view.options")
    def view_options(self) -> None:
        """View the options editor."""
        self.master.view_options()

    @command.command("console.view.help")
    def view_help(self) -> None:
        """View help."""
        self.master.view_help()

    @command.command("console.view.flow")
    def view_flow(self, flow: flow.Flow) -> None:
        """View a flow."""
        if hasattr(flow, "request"):
            # FIME: Also set focus?
            self.master.view_flow(flow)

    @command.command("console.exit")
    def exit(self) -> None:
        """Exit mitmproxy."""
        raise urwid.ExitMainLoop

    @command.command("console.view.pop")
    def view_pop(self) -> None:
        """
            Pop a view off the console stack. At the top level, this prompts the
            user to exit mitmproxy.
        """
        signals.pop_view_state.send(self)

    def running(self):
        self.started = True

    def update(self, flows):
        if not flows:
            signals.update_settings.send(self)

    def configure(self, updated):
        if self.started:
            if "console_eventlog" in updated:
                self.master.refresh_view()


def default_keymap(km):
    km.add(":", "console.command ''")
    km.add("?", "console.view.help")
    km.add("C", "console.view.commands")
    km.add("O", "console.view.options")
    km.add("Q", "console.exit")
    km.add("q", "console.view.pop")
    km.add("i", "console.command 'set intercept='")
    km.add("W", "console.command 'set save_stream_file='")

    km.add("A", "flow.resume @all", context="flowlist")
    km.add("a", "flow.resume @focus", context="flowlist")
    km.add("d", "view.remove @focus", context="flowlist")
    km.add("D", "view.duplicate @focus", context="flowlist")
    km.add("e", "set console_eventlog=toggle", context="flowlist")
    km.add("f", "console.command 'set view_filter='", context="flowlist")
    km.add("F", "set console_focus_follow=toggle", context="flowlist")
    km.add("g", "view.go 0", context="flowlist")
    km.add("G", "view.go -1", context="flowlist")
    km.add("m", "flow.mark.toggle @focus", context="flowlist")
    km.add("r", "replay.client @focus", context="flowlist")
    km.add("S", "console.command 'replay.server '")
    km.add("v", "set console_order_reversed=toggle", context="flowlist")
    km.add("U", "flow.mark @all false", context="flowlist")
    km.add("w", "console.command 'save.file @shown '", context="flowlist")
    km.add("X", "flow.kill @focus", context="flowlist")
    km.add("z", "view.remove @all", context="flowlist")
    km.add("Z", "view.remove @hidden", context="flowlist")
    km.add("enter", "console.view.flow @focus", context="flowlist")


class ConsoleMaster(master.Master):

    def __init__(self, options, server):
        super().__init__(options, server)
        self.view = view.View()  # type: view.View
        self.view.sig_view_update.connect(signals.flow_change.send)
        self.stream_path = None
        # This line is just for type hinting
        self.options = self.options  # type: Options
        self.keymap = keymap.Keymap(self)
        default_keymap(self.keymap)
        self.options.errored.connect(self.options_error)

        self.logbuffer = urwid.SimpleListWalker([])

        self.view_stack = []

        signals.call_in.connect(self.sig_call_in)
        signals.pop_view_state.connect(self.sig_pop_view_state)
        signals.replace_view_state.connect(self.sig_replace_view_state)
        signals.push_view_state.connect(self.sig_push_view_state)
        signals.sig_add_log.connect(self.sig_add_log)
        self.addons.add(Logger())
        self.addons.add(*addons.default_addons())
        self.addons.add(
            intercept.Intercept(),
            self.view,
            UnsupportedLog(),
            readfile.ReadFile(),
            ConsoleAddon(self),
        )

        def sigint_handler(*args, **kwargs):
            self.prompt_for_exit()

        signal.signal(signal.SIGINT, sigint_handler)

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        signals.update_settings.send(self)

    def options_error(self, opts, exc):
        signals.status_message.send(
            message=str(exc),
            expire=1
        )

    def prompt_for_exit(self):
        signals.status_prompt_onekey.send(
            self,
            prompt = "Quit",
            keys = (
                ("yes", "y"),
                ("no", "n"),
            ),
            callback = self.quit,
        )

    def sig_add_log(self, sender, e, level):
        if self.options.verbosity < log.log_tier(level):
            return

        if level in ("error", "warn"):
            signals.status_message.send(
                message = "{}: {}".format(level.title(), e)
            )
            e = urwid.Text((level, str(e)))
        else:
            e = urwid.Text(str(e))
        self.logbuffer.append(e)
        if len(self.logbuffer) > EVENTLOG_SIZE:
            self.logbuffer.pop(0)
        if self.options.console_focus_follow:
            self.logbuffer.set_focus(len(self.logbuffer) - 1)

    def sig_call_in(self, sender, seconds, callback, args=()):
        def cb(*_):
            return callback(*args)
        self.loop.set_alarm_in(seconds, cb)

    def sig_replace_view_state(self, sender):
        """
            A view has been pushed onto the stack, and is intended to replace
            the current view rather than creating a new stack entry.
        """
        if len(self.view_stack) > 1:
            del self.view_stack[1]

    def sig_pop_view_state(self, sender):
        """
            Pop the top view off the view stack. If no more views will be left
            after this, prompt for exit.
        """
        if len(self.view_stack) > 1:
            self.view_stack.pop()
            self.loop.widget = self.view_stack[-1]
        else:
            self.prompt_for_exit()

    def sig_push_view_state(self, sender, window):
        """
            Push a new view onto the view stack.
        """
        self.view_stack.append(window)
        self.loop.widget = window
        self.loop.draw_screen()

    def run_script_once(self, command, f):
        sc = self.addons.get("scriptloader")
        try:
            with self.handlecontext():
                sc.run_once(command, [f])
        except ValueError as e:
            signals.add_log("Input error: %s" % e, "warn")

    def refresh_view(self):
        self.view_flowlist()
        signals.replace_view_state.send(self)

    def _readflows(self, path):
        """
        Utitility function that reads a list of flows
        or prints an error to the UI if that fails.
        Returns
            - None, if there was an error.
            - a list of flows, otherwise.
        """
        try:
            return io.read_flows_from_paths(path)
        except exceptions.FlowReadException as e:
            signals.status_message.send(message=str(e))

    def spawn_editor(self, data):
        text = not isinstance(data, bytes)
        fd, name = tempfile.mkstemp('', "mproxy", text=text)
        with open(fd, "w" if text else "wb") as f:
            f.write(data)
        # if no EDITOR is set, assume 'vi'
        c = os.environ.get("EDITOR") or "vi"
        cmd = shlex.split(c)
        cmd.append(name)
        self.ui.stop()
        try:
            subprocess.call(cmd)
        except:
            signals.status_message.send(
                message="Can't start editor: %s" % " ".join(c)
            )
        else:
            with open(name, "r" if text else "rb") as f:
                data = f.read()
        self.ui.start()
        os.unlink(name)
        return data

    def spawn_external_viewer(self, data, contenttype):
        if contenttype:
            contenttype = contenttype.split(";")[0]
            ext = mimetypes.guess_extension(contenttype) or ""
        else:
            ext = ""
        fd, name = tempfile.mkstemp(ext, "mproxy")
        os.write(fd, data)
        os.close(fd)

        # read-only to remind the user that this is a view function
        os.chmod(name, stat.S_IREAD)

        cmd = None
        shell = False

        if contenttype:
            c = mailcap.getcaps()
            cmd, _ = mailcap.findmatch(c, contenttype, filename=name)
            if cmd:
                shell = True
        if not cmd:
            # hm which one should get priority?
            c = os.environ.get("PAGER") or os.environ.get("EDITOR")
            if not c:
                c = "less"
            cmd = shlex.split(c)
            cmd.append(name)
        self.ui.stop()
        try:
            subprocess.call(cmd, shell=shell)
        except:
            signals.status_message.send(
                message="Can't start external viewer: %s" % " ".join(c)
            )
        self.ui.start()
        os.unlink(name)

    def set_palette(self, options, updated):
        self.ui.register_palette(
            palettes.palettes[options.console_palette].palette(
                options.console_palette_transparent
            )
        )
        self.ui.clear()

    def ticker(self, *userdata):
        changed = self.tick(timeout=0)
        if changed:
            self.loop.draw_screen()
        self.loop.set_alarm_in(0.01, self.ticker)

    def run(self):
        self.ui = urwid.raw_display.Screen()
        self.ui.set_terminal_properties(256)
        self.set_palette(self.options, None)
        self.options.subscribe(
            self.set_palette,
            ["console_palette", "console_palette_transparent"]
        )
        self.loop = urwid.MainLoop(
            urwid.SolidFill("x"),
            screen = self.ui,
            handle_mouse = self.options.console_mouse,
        )
        self.ab = statusbar.ActionBar(self)

        self.loop.set_alarm_in(0.01, self.ticker)
        self.loop.set_alarm_in(
            0.0001,
            lambda *args: self.view_flowlist()
        )

        self.start()
        try:
            self.loop.run()
        except Exception:
            self.loop.stop()
            sys.stdout.flush()
            print(traceback.format_exc(), file=sys.stderr)
            print("mitmproxy has crashed!", file=sys.stderr)
            print("Please lodge a bug report at:", file=sys.stderr)
            print("\thttps://github.com/mitmproxy/mitmproxy", file=sys.stderr)
            print("Shutting down...", file=sys.stderr)
        finally:
            sys.stderr.flush()
            super().shutdown()

    def shutdown(self):
        raise urwid.ExitMainLoop

    def overlay(self, widget, **kwargs):
        signals.push_view_state.send(
            self,
            window = overlay.SimpleOverlay(
                self,
                widget,
                self.loop.widget,
                widget.width,
                **kwargs
            )
        )

    def view_help(self):
        hc = self.view_stack[-1].helpctx
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                help.HelpView(hc),
                None,
                statusbar.StatusBar(self, help.footer),
                None,
                "help"
            )
        )

    def view_options(self):
        for i in self.view_stack:
            if isinstance(i["body"], options.Options):
                return
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                options.Options(self),
                None,
                statusbar.StatusBar(self, options.footer),
                options.help_context,
                "options"
            )
        )

    def view_commands(self):
        for i in self.view_stack:
            if isinstance(i["body"], commands.Commands):
                return
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                commands.Commands(self),
                None,
                statusbar.StatusBar(self, commands.footer),
                commands.help_context,
                "commands"
            )
        )

    def view_grideditor(self, ge):
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                ge,
                None,
                statusbar.StatusBar(self, grideditor.base.FOOTER),
                ge.make_help(),
                "grideditor"
            )
        )

    def view_flowlist(self):
        if self.ui.started:
            self.ui.clear()

        if self.options.console_eventlog:
            body = flowlist.BodyPile(self)
        else:
            body = flowlist.FlowListBox(self)

        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                body,
                None,
                statusbar.StatusBar(self, flowlist.footer),
                flowlist.help_context,
                "flowlist"
            )
        )

    def view_flow(self, flow, tab_offset=0):
        self.view.focus.flow = flow
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                flowview.FlowView(self, self.view, flow, tab_offset),
                flowview.FlowViewHeader(self, flow),
                statusbar.StatusBar(self, flowview.footer),
                flowview.help_context,
                "flowview"
            )
        )

    def _write_flows(self, path, flows):
        with open(path, "wb") as f:
            fw = io.FlowWriter(f)
            for i in flows:
                fw.add(i)

    def save_one_flow(self, path, flow):
        return self._write_flows(path, [flow])

    def save_flows(self, path):
        return self._write_flows(path, self.view)

    def load_flows_callback(self, path):
        ret = self.load_flows_path(path)
        return ret or "Flows loaded from %s" % path

    def load_flows_path(self, path):
        reterr = None
        try:
            master.Master.load_flows_file(self, path)
        except exceptions.FlowReadException as e:
            reterr = str(e)
        signals.flowlist_change.send(self)
        return reterr

    def quit(self, a):
        if a != "n":
            self.shutdown()

    def clear_events(self):
        self.logbuffer[:] = []
