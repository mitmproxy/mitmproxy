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
import typing

import urwid

from mitmproxy import ctx
from mitmproxy import addons
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import master
from mitmproxy import log
from mitmproxy import flow
from mitmproxy.addons import intercept
from mitmproxy.addons import readfile
from mitmproxy.addons import view
from mitmproxy.tools.console import keymap
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
        An addon that exposes console-specific commands, and hooks into required
        events.
    """
    def __init__(self, master):
        self.master = master
        self.started = False

    @command.command("console.choose")
    def console_choose(
        self, prompt: str, choices: typing.Sequence[str], *cmd: typing.Sequence[str]
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

        self.master.overlay(overlay.Chooser(prompt, choices, "", callback))
        ctx.log.info(choices)

    @command.command("console.choose.cmd")
    def console_choose_cmd(
        self, prompt: str, choicecmd: str, *cmd: typing.Sequence[str]
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

        self.master.overlay(overlay.Chooser(prompt, choices, "", callback))
        ctx.log.info(choices)

    @command.command("console.command")
    def console_command(self, *partial: typing.Sequence[str]) -> None:
        """
        Prompt the user to edit a command with a (possilby empty) starting value.
        """
        signals.status_prompt_command.send(partial=" ".join(partial) + " ")  # type: ignore

    @command.command("console.view.commands")
    def view_commands(self) -> None:
        """View the commands list."""
        self.master.switch_view("commands")

    @command.command("console.view.options")
    def view_options(self) -> None:
        """View the options editor."""
        self.master.switch_view("options")

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
        raise urwid.ExitMainLoop

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

    def running(self):
        self.started = True

    def update(self, flows):
        if not flows:
            signals.update_settings.send(self)
        for f in flows:
            signals.flow_change.send(self, flow=f)

    def configure(self, updated):
        if self.started:
            if "console_eventlog" in updated:
                pass


def default_keymap(km):
    km.add(":", "console.command ''", ["global"])
    km.add("?", "console.view.help", ["global"])
    km.add("C", "console.view.commands", ["global"])
    km.add("O", "console.view.options", ["global"])
    km.add("Q", "console.exit", ["global"])
    km.add("q", "console.view.pop", ["global"])
    km.add("i", "console.command set intercept=", ["global"])
    km.add("W", "console.command set save_stream_file=", ["global"])

    km.add("A", "flow.resume @all", ["flowlist", "flowview"])
    km.add("a", "flow.resume @focus", ["flowlist", "flowview"])
    km.add(
        "b", "console.command cut.save s.content|@focus ''",
        ["flowlist", "flowview"]
    )
    km.add("d", "view.remove @focus", ["flowlist", "flowview"])
    km.add("D", "view.duplicate @focus", ["flowlist", "flowview"])
    km.add("e", "set console_eventlog=toggle", ["flowlist"])
    km.add(
        "E",
        "console.choose.cmd Format export.formats "
        "console.command export.file {choice} @focus ''",
        ["flowlist", "flowview"]
    )
    km.add("f", "console.command 'set view_filter='", ["flowlist"])
    km.add("F", "set console_focus_follow=toggle", ["flowlist"])
    km.add("g", "view.go 0", ["flowlist"])
    km.add("G", "view.go -1", ["flowlist"])
    km.add("l", "console.command cut.clip ", ["flowlist", "flowview"])
    km.add("L", "console.command view.load ", ["flowlist"])
    km.add("m", "flow.mark.toggle @focus", ["flowlist"])
    km.add("M", "view.marked.toggle", ["flowlist"])
    km.add(
        "n",
        "console.command view.create get https://google.com",
        ["flowlist"]
    )
    km.add(
        "o",
        "console.choose.cmd Order view.order.options "
        "set console_order={choice}",
        ["flowlist"]
    )
    km.add("r", "replay.client @focus", ["flowlist", "flowview"])
    km.add("S", "console.command 'replay.server '", ["flowlist"])
    km.add("v", "set console_order_reversed=toggle", ["flowlist"])
    km.add("U", "flow.mark @all false", ["flowlist"])
    km.add("w", "console.command 'save.file @shown '", ["flowlist"])
    km.add("V", "flow.revert @focus", ["flowlist", "flowview"])
    km.add("X", "flow.kill @focus", ["flowlist"])
    km.add("z", "view.remove @all", ["flowlist"])
    km.add("Z", "view.remove @hidden", ["flowlist"])
    km.add("|", "console.command 'script.run @focus '", ["flowlist", "flowview"])
    km.add("enter", "console.view.flow @focus", ["flowlist"])

    km.add(
        "e",
        "console.choose.cmd Part console.edit.focus.options "
        "console.edit.focus {choice}",
        ["flowview"]
    )
    km.add("w", "console.command 'save.file @focus '", ["flowview"])
    km.add(" ", "view.focus.next", ["flowview"])
    km.add(
        "o",
        "console.choose.cmd Order view.order.options "
        "set console_order={choice}",
        ["flowlist"]
    )

    km.add(
        "v",
        "console.choose \"View Part\" request,response "
        "console.bodyview @focus {choice}",
        ["flowview"]
    )
    km.add("p", "view.focus.prev", ["flowview"])


class ConsoleMaster(master.Master):

    def __init__(self, options, server):
        super().__init__(options, server)
        self.view = view.View()  # type: view.View
        self.stream_path = None
        # This line is just for type hinting
        self.options = self.options  # type: Options
        self.keymap = keymap.Keymap(self)
        default_keymap(self.keymap)
        self.options.errored.connect(self.options_error)

        self.logbuffer = urwid.SimpleListWalker([])

        self.view_stack = []

        signals.call_in.connect(self.sig_call_in)
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

        self.ab = None
        self.window = None

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
        self.window = window.Window(self)
        self.loop.widget = self.window

        self.loop.set_alarm_in(0.01, self.ticker)
        self.loop.set_alarm_in(
            0.0001,
            lambda *args: self.switch_view("flowlist")
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

    def sig_exit_overlay(self, *args, **kwargs):
        self.loop.widget = self.window

    def overlay(self, widget, **kwargs):
        self.loop.widget = overlay.SimpleOverlay(
            self, widget, self.loop.widget, widget.width, **kwargs
        )

    def switch_view(self, name):
        self.window.push(name)

    def quit(self, a):
        if a != "n":
            self.shutdown()

    def clear_events(self):
        self.logbuffer[:] = []
