import asyncio
import contextlib
import mimetypes
import os.path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
from typing import TypeVar

import urwid
from tornado.platform.asyncio import AddThreadSelectorEventLoop

from mitmproxy import addons
from mitmproxy import log
from mitmproxy import master
from mitmproxy import options
from mitmproxy.addons import errorcheck
from mitmproxy.addons import eventstore
from mitmproxy.addons import intercept
from mitmproxy.addons import readfile
from mitmproxy.addons import view
from mitmproxy.tools.console import consoleaddons
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import palettes
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import window
from mitmproxy.utils import strutils

T = TypeVar("T", str, bytes)


class ConsoleMaster(master.Master):
    def __init__(self, opts: options.Options) -> None:
        super().__init__(opts)

        self.view: view.View = view.View()
        self.events = eventstore.EventStore()
        self.events.sig_add.connect(self.sig_add_log)

        self.stream_path = None
        self.keymap = keymap.Keymap(self)
        defaultkeys.map(self.keymap)
        self.options.errored.connect(self.options_error)

        self.addons.add(*addons.default_addons())
        self.addons.add(
            intercept.Intercept(),
            self.view,
            self.events,
            readfile.ReadFile(),
            consoleaddons.ConsoleAddon(self),
            keymap.KeymapConfig(self),
            errorcheck.ErrorCheck(repeat_errors_on_stderr=True),
        )

        self.window: window.Window | None = None

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        signals.update_settings.send()

    def options_error(self, exc) -> None:
        signals.status_message.send(message=str(exc), expire=1)

    def prompt_for_exit(self) -> None:
        signals.status_prompt_onekey.send(
            prompt="Quit",
            keys=[
                ("yes", "y"),
                ("no", "n"),
            ],
            callback=self.quit,
        )

    def sig_add_log(self, entry: log.LogEntry):
        if log.log_tier(self.options.console_eventlog_verbosity) < log.log_tier(
            entry.level
        ):
            return
        if entry.level in ("error", "warn", "alert"):
            signals.status_message.send(
                message=(
                    entry.level,
                    f"{entry.level.title()}: {str(entry.msg).lstrip()}",
                ),
                expire=5,
            )

    def sig_call_in(self, seconds, callback):
        def cb(*_):
            return callback()

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

    def get_editor(self) -> str:
        # based upon https://github.com/pallets/click/blob/main/src/click/_termui_impl.py
        if m := os.environ.get("MITMPROXY_EDITOR"):
            return m
        if m := os.environ.get("EDITOR"):
            return m
        for editor in "sensible-editor", "nano", "vim":
            if shutil.which(editor):
                return editor
        if os.name == "nt":
            return "notepad"
        else:
            return "vi"

    def get_hex_editor(self) -> str:
        editors = ["ghex", "bless", "hexedit", "hxd", "hexer", "hexcurse"]
        for editor in editors:
            if shutil.which(editor):
                return editor
        return self.get_editor()

    def spawn_editor(self, data: T) -> T:
        text = isinstance(data, str)
        fd, name = tempfile.mkstemp("", "mitmproxy", text=text)
        with_hexeditor = isinstance(data, bytes) and strutils.is_mostly_bin(data)
        with open(fd, "w" if text else "wb") as f:
            f.write(data)
        if with_hexeditor:
            c = self.get_hex_editor()
        else:
            c = self.get_editor()
        cmd = shlex.split(c)
        cmd.append(name)
        with self.uistopped():
            try:
                subprocess.call(cmd)
            except Exception:
                signals.status_message.send(message="Can't start editor: %s" % c)
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

        # hm which one should get priority?
        c = (
            os.environ.get("MITMPROXY_EDITOR")
            or os.environ.get("PAGER")
            or os.environ.get("EDITOR")
        )
        if not c:
            c = "less"
        cmd = shlex.split(c)
        cmd.append(name)

        with self.uistopped():
            try:
                subprocess.call(cmd, shell=False)
            except Exception:
                signals.status_message.send(
                    message="Can't start external viewer: %s" % " ".join(c)
                )
        # add a small delay before deletion so that the file is not removed before being loaded by the viewer
        t = threading.Timer(1.0, os.unlink, args=[name])
        t.start()

    def set_palette(self, *_) -> None:
        self.ui.register_palette(
            palettes.palettes[self.options.console_palette].palette(
                self.options.console_palette_transparent
            )
        )
        self.ui.clear()

    def inject_key(self, key):
        self.loop.process_input([key])

    async def running(self) -> None:
        if not sys.stdout.isatty():
            print(
                "Error: mitmproxy's console interface requires a tty. "
                "Please run mitmproxy in an interactive shell environment.",
                file=sys.stderr,
            )
            sys.exit(1)

        detected_encoding = urwid.detected_encoding.lower()
        if os.name != "nt" and detected_encoding and "utf" not in detected_encoding:
            print(
                f"mitmproxy expects a UTF-8 console environment, not {urwid.detected_encoding!r}. "
                f"Set your LANG environment variable to something like en_US.UTF-8.",
                file=sys.stderr,
            )
            # Experimental (04/2022): We just don't exit here and see if/how that affects users.
            # sys.exit(1)
        urwid.set_encoding("utf8")

        signals.call_in.connect(self.sig_call_in)
        self.ui = window.Screen()
        self.ui.set_terminal_properties(256)
        self.set_palette(None)
        self.options.subscribe(
            self.set_palette, ["console_palette", "console_palette_transparent"]
        )

        loop = asyncio.get_running_loop()
        if isinstance(loop, getattr(asyncio, "ProactorEventLoop", tuple())):
            # fix for https://bugs.python.org/issue37373
            loop = AddThreadSelectorEventLoop(loop)  # type: ignore
        self.loop = urwid.MainLoop(
            urwid.SolidFill("x"),
            event_loop=urwid.AsyncioEventLoop(loop=loop),
            screen=self.ui,
            handle_mouse=self.options.console_mouse,
        )
        self.window = window.Window(self)
        self.loop.widget = self.window
        self.window.refresh()

        self.loop.start()

        await super().running()

    async def done(self):
        self.loop.stop()
        await super().done()

    def overlay(self, widget, **kwargs):
        assert self.window
        self.window.set_overlay(widget, **kwargs)

    def switch_view(self, name):
        assert self.window
        self.window.push(name)

    def quit(self, a):
        if a != "n":
            self.shutdown()
