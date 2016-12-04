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
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import master
from mitmproxy import io
from mitmproxy import log
from mitmproxy.addons import view
from mitmproxy.addons import intercept
import mitmproxy.options
from mitmproxy.tools.console import flowlist
from mitmproxy.tools.console import flowview
from mitmproxy.tools.console import grideditor
from mitmproxy.tools.console import help
from mitmproxy.tools.console import options
from mitmproxy.tools.console import palettepicker
from mitmproxy.tools.console import palettes
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import statusbar
from mitmproxy.tools.console import window
from mitmproxy.utils import strutils

from mitmproxy.net import tcp

EVENTLOG_SIZE = 10000


class Logger:
    def log(self, evt):
        signals.add_log(evt.msg, evt.level)


class ConsoleMaster(master.Master):
    palette = []

    def __init__(self, options, server):
        super().__init__(options, server)
        self.view = view.View()  # type: view.View
        self.view.sig_view_update.connect(signals.flow_change.send)
        self.stream_path = None
        # This line is just for type hinting
        self.options = self.options  # type: Options
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
        self.addons.add(intercept.Intercept(), self.view)

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
        if self.options.focus_follow:
            self.logbuffer.set_focus(len(self.logbuffer) - 1)

    def sig_call_in(self, sender, seconds, callback, args=()):
        def cb(*_):
            return callback(*args)
        self.loop.set_alarm_in(seconds, cb)

    def sig_replace_view_state(self, sender):
        """
            A view has been pushed onto the stack, and is intended to replace
            the current view rather tha creating a new stack entry.
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
        except mitmproxy.exceptions.AddonError as e:
            signals.add_log("Script error: %s" % e, "warn")

    def toggle_eventlog(self):
        self.options.eventlog = not self.options.eventlog
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
            palettes.palettes[options.palette].palette(
                options.palette_transparent
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
            ["palette", "palette_transparent"]
        )
        self.loop = urwid.MainLoop(
            urwid.SolidFill("x"),
            screen = self.ui,
            handle_mouse = not self.options.no_mouse,
        )
        self.ab = statusbar.ActionBar()

        if self.options.rfile:
            ret = self.load_flows_path(self.options.rfile)
            if ret and self.view.store_count():
                signals.add_log(
                    "File truncated or corrupted. "
                    "Loaded as many flows as possible.",
                    "error"
                )
            elif ret and not self.view.store_count():
                self.shutdown()
                print("Could not load file: {}".format(ret), file=sys.stderr)
                sys.exit(1)

        self.loop.set_alarm_in(0.01, self.ticker)
        if self.options.http2 and not tcp.HAS_ALPN:  # pragma: no cover
            def http2err(*args, **kwargs):
                signals.status_message.send(
                    message = "HTTP/2 disabled - OpenSSL 1.0.2+ required."
                              " Use --no-http2 to silence this warning.",
                    expire=5
                )
            self.loop.set_alarm_in(0.01, http2err)

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
            self.shutdown()

    def view_help(self, helpctx):
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                help.HelpView(helpctx),
                None,
                statusbar.StatusBar(self, help.footer),
                None
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
            )
        )

    def view_palette_picker(self):
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                palettepicker.PalettePicker(self),
                None,
                statusbar.StatusBar(self, palettepicker.footer),
                palettepicker.help_context,
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
                ge.make_help()
            )
        )

    def view_flowlist(self):
        if self.ui.started:
            self.ui.clear()

        if self.options.eventlog:
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
                flowlist.help_context
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
                flowview.help_context
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
            raise urwid.ExitMainLoop

    def clear_events(self):
        self.logbuffer[:] = []

    # Handlers
    @controller.handler
    def websocket_message(self, f):
        super().websocket_message(f)
        message = f.messages[-1]
        signals.add_log(message.info, "info")
        signals.add_log(strutils.bytes_to_escaped_str(message.content), "debug")

    @controller.handler
    def websocket_end(self, f):
        super().websocket_end(f)
        signals.add_log("WebSocket connection closed by {}: {} {}, {}".format(
            f.close_sender,
            f.close_code,
            f.close_message,
            f.close_reason), "info")

    @controller.handler
    def tcp_message(self, f):
        super().tcp_message(f)
        message = f.messages[-1]
        direction = "->" if message.from_client else "<-"
        signals.add_log("{client} {direction} tcp {direction} {server}".format(
            client=repr(f.client_conn.address),
            server=repr(f.server_conn.address),
            direction=direction,
        ), "info")
        signals.add_log(strutils.bytes_to_escaped_str(message.content), "debug")
