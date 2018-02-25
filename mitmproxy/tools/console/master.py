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
import typing  # noqa
import contextlib

import urwid

from mitmproxy import addons
from mitmproxy import master
from mitmproxy import log
from mitmproxy.addons import intercept
from mitmproxy.addons import eventstore
from mitmproxy.addons import readfile
from mitmproxy.addons import view
from mitmproxy.tools.console import consoleaddons
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import palettes
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import window


class ConsoleMaster(master.Master):

    def __init__(self, opts):
        super().__init__(opts)

        self.start_err = None  # type: typing.Optional[log.LogEntry]

        self.view = view.View()  # type: view.View
        self.events = eventstore.EventStore()
        self.events.sig_add.connect(self.sig_add_log)

        self.stream_path = None
        self.keymap = keymap.Keymap(self)
        defaultkeys.map(self.keymap)
        self.options.errored.connect(self.options_error)

        self.view_stack = []

        signals.call_in.connect(self.sig_call_in)
        self.addons.add(*addons.default_addons())
        self.addons.add(
            intercept.Intercept(),
            self.view,
            self.events,
            consoleaddons.UnsupportedLog(),
            readfile.ReadFile(),
            consoleaddons.ConsoleAddon(self),
        )

        def sigint_handler(*args, **kwargs):
            self.prompt_for_exit()

        signal.signal(signal.SIGINT, sigint_handler)

        self.window = None

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
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

    def sig_add_log(self, event_store, entry: log.LogEntry):
        if log.log_tier(self.options.console_eventlog_verbosity) < log.log_tier(entry.level):
            return
        if entry.level in ("error", "warn", "alert"):
            if self.first_tick:
                self.start_err = entry
            else:
                signals.status_message.send(
                    message=(entry.level, "{}: {}".format(entry.level.title(), entry.msg)),
                    expire=5
                )

    def sig_call_in(self, sender, seconds, callback, args=()):
        def cb(*_):
            return callback(*args)
        self.loop.set_alarm_in(seconds, cb)

    @contextlib.contextmanager
    def uistopped(self):
        self.loop.stop()
        try:
            yield
        finally:
            self.loop.start()
            self.loop.screen_size = None
            self.loop.draw_screen()

    def spawn_editor(self, data):
        text = not isinstance(data, bytes)
        fd, name = tempfile.mkstemp('', "mproxy", text=text)
        with open(fd, "w" if text else "wb") as f:
            f.write(data)
        # if no EDITOR is set, assume 'vi'
        c = os.environ.get("EDITOR") or "vi"
        cmd = shlex.split(c)
        cmd.append(name)
        with self.uistopped():
            try:
                subprocess.call(cmd)
            except:
                signals.status_message.send(
                    message="Can't start editor: %s" % " ".join(c)
                )
            else:
                with open(name, "r" if text else "rb") as f:
                    data = f.read()
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
        with self.uistopped():
            try:
                subprocess.call(cmd, shell=shell)
            except:
                signals.status_message.send(
                    message="Can't start external viewer: %s" % " ".join(c)
                )
        os.unlink(name)

    def set_palette(self, opts, updated):
        self.ui.register_palette(
            palettes.palettes[opts.console_palette].palette(
                opts.console_palette_transparent
            )
        )
        self.ui.clear()

    def ticker(self, *userdata):
        changed = self.tick(timeout=0)
        if changed:
            self.loop.draw_screen()
        self.loop.set_alarm_in(0.01, self.ticker)

    def inject_key(self, key):
        self.loop.process_input([key])

    def run(self):
        if not sys.stdout.isatty():
            print("Error: mitmproxy's console interface requires a tty. "
                  "Please run mitmproxy in an interactive shell environment.", file=sys.stderr)
            sys.exit(1)

        self.ui = window.Screen()
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

        self.window = window.Window(self)
        self.loop.widget = self.window
        self.window.refresh()

        self.loop.set_alarm_in(0.01, self.ticker)

        if self.start_err:
            def display_err(*_):
                self.sig_add_log(None, self.start_err)
                self.start_err = None
            self.loop.set_alarm_in(0.01, display_err)

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
        self.window.set_overlay(widget, **kwargs)

    def switch_view(self, name):
        self.window.push(name)

    def quit(self, a):
        if a != "n":
            self.shutdown()
