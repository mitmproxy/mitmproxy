from __future__ import absolute_import, print_function, division

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
import weakref

import six
import urwid
from typing import Optional  # noqa

from mitmproxy import builtins
from mitmproxy import contentviews
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import script
from mitmproxy import utils
import mitmproxy.options
from mitmproxy.console import flowlist
from mitmproxy.console import flowview
from mitmproxy.console import grideditor
from mitmproxy.console import help
from mitmproxy.console import options
from mitmproxy.console import palettepicker
from mitmproxy.console import palettes
from mitmproxy.console import signals
from mitmproxy.console import statusbar
from mitmproxy.console import window
from mitmproxy.filt import FMarked
from netlib import tcp, strutils

EVENTLOG_SIZE = 500


class ConsoleState(flow.State):

    def __init__(self):
        flow.State.__init__(self)
        self.focus = None
        self.follow_focus = None
        self.default_body_view = contentviews.get("Auto")
        self.flowsettings = weakref.WeakKeyDictionary()
        self.last_search = None
        self.last_filter = ""
        self.mark_filter = False

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        signals.update_settings.send(self)

    def add_flow_setting(self, flow, key, value):
        d = self.flowsettings.setdefault(flow, {})
        d[key] = value

    def get_flow_setting(self, flow, key, default=None):
        d = self.flowsettings.get(flow, {})
        return d.get(key, default)

    def add_flow(self, f):
        super(ConsoleState, self).add_flow(f)
        self.update_focus()
        return f

    def update_flow(self, f):
        super(ConsoleState, self).update_flow(f)
        self.update_focus()
        return f

    def set_view_filter(self, txt):
        ret = super(ConsoleState, self).set_view_filter(txt)
        self.set_focus(self.focus)
        return ret

    def get_focus(self):
        if not self.view or self.focus is None:
            return None, None
        return self.view[self.focus], self.focus

    def set_focus(self, idx):
        if self.view:
            if idx is None or idx < 0:
                idx = 0
            elif idx >= len(self.view):
                idx = len(self.view) - 1
            self.focus = idx
        else:
            self.focus = None

    def update_focus(self):
        if self.focus is None:
            self.set_focus(0)
        elif self.follow_focus:
            self.set_focus(len(self.view) - 1)

    def set_focus_flow(self, f):
        self.set_focus(self.view.index(f))

    def get_from_pos(self, pos):
        if len(self.view) <= pos or pos < 0:
            return None, None
        return self.view[pos], pos

    def get_next(self, pos):
        return self.get_from_pos(pos + 1)

    def get_prev(self, pos):
        return self.get_from_pos(pos - 1)

    def delete_flow(self, f):
        if f in self.view and self.view.index(f) <= self.focus:
            self.focus -= 1
        if self.focus < 0:
            self.focus = None
        ret = super(ConsoleState, self).delete_flow(f)
        self.set_focus(self.focus)
        return ret

    def get_nearest_matching_flow(self, flow, filt):
        fidx = self.view.index(flow)
        dist = 1

        fprev = fnext = True
        while fprev or fnext:
            fprev, _ = self.get_from_pos(fidx - dist)
            fnext, _ = self.get_from_pos(fidx + dist)

            if fprev and fprev.match(filt):
                return fprev
            elif fnext and fnext.match(filt):
                return fnext

            dist += 1

        return None

    def enable_marked_filter(self):
        marked_flows = [f for f in self.flows if f.marked]
        if not marked_flows:
            return

        marked_filter = "~%s" % FMarked.code

        # Save Focus
        last_focus, _ = self.get_focus()
        nearest_marked = self.get_nearest_matching_flow(last_focus, marked_filter)

        self.last_filter = self.filter_txt
        self.set_view_filter(marked_filter)

        # Restore Focus
        if last_focus.marked:
            self.set_focus_flow(last_focus)
        else:
            self.set_focus_flow(nearest_marked)

        self.mark_filter = True

    def disable_marked_filter(self):
        marked_filter = "~%s" % FMarked.code

        # Save Focus
        last_focus, _ = self.get_focus()
        nearest_marked = self.get_nearest_matching_flow(last_focus, marked_filter)

        self.set_view_filter(self.last_filter)
        self.last_filter = ""

        # Restore Focus
        if last_focus.marked:
            self.set_focus_flow(last_focus)
        else:
            self.set_focus_flow(nearest_marked)

        self.mark_filter = False

    def clear(self):
        marked_flows = [f for f in self.view if f.marked]
        super(ConsoleState, self).clear()

        for f in marked_flows:
            self.add_flow(f)
            f.marked = True

        if len(self.flows.views) == 0:
            self.focus = None
        else:
            self.focus = 0
        self.set_focus(self.focus)


class Options(mitmproxy.options.Options):
    def __init__(
            self,
            eventlog=False,  # type: bool
            follow=False,  # type: bool
            intercept=False,  # type: bool
            filter=None,  # type: Optional[str]
            palette=None,  # type: Optional[str]
            palette_transparent=False,  # type: bool
            no_mouse=False,  # type: bool
            **kwargs
    ):
        self.eventlog = eventlog
        self.follow = follow
        self.intercept = intercept
        self.filter = filter
        self.palette = palette
        self.palette_transparent = palette_transparent
        self.no_mouse = no_mouse
        super(Options, self).__init__(**kwargs)


class ConsoleMaster(flow.FlowMaster):
    palette = []

    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, options, server, ConsoleState())
        self.stream_path = None
        # This line is just for type hinting
        self.options = self.options  # type: Options
        self.options.errored.connect(self.options_error)

        r = self.set_intercept(options.intercept)
        if r:
            print("Intercept error: {}".format(r), file=sys.stderr)
            sys.exit(1)

        if options.filter:
            self.set_view_filter(options.filter)

        self.set_stream_large_bodies(options.stream_large_bodies)

        self.palette = options.palette
        self.palette_transparent = options.palette_transparent

        self.logbuffer = urwid.SimpleListWalker([])
        self.follow = options.follow

        if options.client_replay:
            self.client_playback_path(options.client_replay)

        self.view_stack = []

        if options.app:
            self.start_app(self.options.app_host, self.options.app_port)

        signals.call_in.connect(self.sig_call_in)
        signals.pop_view_state.connect(self.sig_pop_view_state)
        signals.replace_view_state.connect(self.sig_replace_view_state)
        signals.push_view_state.connect(self.sig_push_view_state)
        signals.sig_add_log.connect(self.sig_add_log)
        self.addons.add(options, *builtins.default_addons())

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        signals.update_settings.send(self)

    def options_error(self, opts, exc):
        signals.status_message.send(
            message=str(exc),
            expire=1
        )

    def sig_add_log(self, sender, e, level):
        if self.options.verbosity < utils.log_tier(level):
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
        self.logbuffer.set_focus(len(self.logbuffer) - 1)

    def add_log(self, e, level):
        signals.add_log(e, level)

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
            signals.status_prompt_onekey.send(
                self,
                prompt = "Quit",
                keys = (
                    ("yes", "y"),
                    ("no", "n"),
                ),
                callback = self.quit,
            )

    def sig_push_view_state(self, sender, window):
        """
            Push a new view onto the view stack.
        """
        self.view_stack.append(window)
        self.loop.widget = window
        self.loop.draw_screen()

    def _run_script_method(self, method, s, f):
        status, val = s.run(method, f)
        if val:
            if status:
                signals.add_log("Method %s return: %s" % (method, val), "debug")
            else:
                signals.add_log(
                    "Method %s error: %s" %
                    (method, val[1]), "error")

    def run_script_once(self, command, f):
        if not command:
            return
        signals.add_log("Running script on flow: %s" % command, "debug")

        try:
            s = script.Script(command)
            s.load()
        except script.ScriptException as e:
            signals.status_message.send(
                message='Error loading "{}".'.format(command)
            )
            signals.add_log('Error loading "{}":\n{}'.format(command, e), "error")
            return

        if f.request:
            self._run_script_method("request", s, f)
        if f.response:
            self._run_script_method("response", s, f)
        if f.error:
            self._run_script_method("error", s, f)
        s.unload()
        signals.flow_change.send(self, flow = f)

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
            return flow.read_flows_from_paths(path)
        except exceptions.FlowReadException as e:
            signals.status_message.send(message=str(e))

    def client_playback_path(self, path):
        if not isinstance(path, list):
            path = [path]
        flows = self._readflows(path)
        if flows:
            self.start_client_playback(flows, False)

    def spawn_editor(self, data):
        text = not isinstance(data, bytes)
        fd, name = tempfile.mkstemp('', "mproxy", text=text)
        if six.PY2:
            os.close(fd)
            with open(name, "w" if text else "wb") as f:
                f.write(data)
        else:
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

    def set_palette(self, name):
        self.palette = name
        self.ui.register_palette(
            palettes.palettes[name].palette(self.palette_transparent)
        )
        self.ui.clear()

    def ticker(self, *userdata):
        changed = self.tick(timeout=0)
        if changed:
            self.loop.draw_screen()
            signals.update_settings.send()
        self.loop.set_alarm_in(0.01, self.ticker)

    def run(self):
        self.ui = urwid.raw_display.Screen()
        self.ui.set_terminal_properties(256)
        self.set_palette(self.palette)
        self.loop = urwid.MainLoop(
            urwid.SolidFill("x"),
            screen = self.ui,
            handle_mouse = not self.options.no_mouse,
        )
        self.ab = statusbar.ActionBar()

        if self.options.rfile:
            ret = self.load_flows_path(self.options.rfile)
            if ret and self.state.flow_count():
                signals.add_log(
                    "File truncated or corrupted. "
                    "Loaded as many flows as possible.",
                    "error"
                )
            elif ret and not self.state.flow_count():
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

        # It's not clear why we need to handle this explicitly - without this,
        # mitmproxy hangs on keyboard interrupt. Remove if we ever figure it
        # out.
        def exit(s, f):
            raise urwid.ExitMainLoop
        signal.signal(signal.SIGINT, exit)

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
        if self.state.follow_focus:
            self.state.set_focus(self.state.flow_count())

        if self.options.eventlog:
            body = flowlist.BodyPile(self)
        else:
            body = flowlist.FlowListBox(self)

        if self.follow:
            self.toggle_follow_flows()

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
        self.state.set_focus_flow(flow)
        signals.push_view_state.send(
            self,
            window = window.Window(
                self,
                flowview.FlowView(self, self.state, flow, tab_offset),
                flowview.FlowViewHeader(self, flow),
                statusbar.StatusBar(self, flowview.footer),
                flowview.help_context
            )
        )

    def _write_flows(self, path, flows):
        if not path:
            return
        path = os.path.expanduser(path)
        try:
            f = open(path, "wb")
            fw = flow.FlowWriter(f)
            for i in flows:
                fw.add(i)
            f.close()
        except IOError as v:
            signals.status_message.send(message=v.strerror)

    def save_one_flow(self, path, flow):
        return self._write_flows(path, [flow])

    def save_flows(self, path):
        return self._write_flows(path, self.state.view)

    def load_flows_callback(self, path):
        if not path:
            return
        ret = self.load_flows_path(path)
        return ret or "Flows loaded from %s" % path

    def load_flows_path(self, path):
        reterr = None
        try:
            flow.FlowMaster.load_flows_file(self, path)
        except exceptions.FlowReadException as e:
            reterr = str(e)
        signals.flowlist_change.send(self)
        return reterr

    def accept_all(self):
        self.state.accept_all(self)

    def set_view_filter(self, txt):
        v = self.state.set_view_filter(txt)
        signals.flowlist_change.send(self)
        return v

    def set_intercept(self, txt):
        return self.state.set_intercept(txt)

    def change_default_display_mode(self, t):
        v = contentviews.get_by_shortcut(t)
        self.state.default_body_view = v
        self.refresh_focus()

    def edit_scripts(self, scripts):
        self.options.scripts = [x[0] for x in scripts]

    def stop_client_playback_prompt(self, a):
        if a != "n":
            self.stop_client_playback()

    def stop_server_playback_prompt(self, a):
        if a != "n":
            self.stop_server_playback()

    def quit(self, a):
        if a != "n":
            raise urwid.ExitMainLoop

    def shutdown(self):
        self.state.killall(self)
        flow.FlowMaster.shutdown(self)

    def clear_flows(self):
        self.state.clear()
        signals.flowlist_change.send(self)

    def toggle_follow_flows(self):
        # toggle flow follow
        self.state.follow_focus = not self.state.follow_focus
        # jump to most recent flow if follow is now on
        if self.state.follow_focus:
            self.state.set_focus(self.state.flow_count())
            signals.flowlist_change.send(self)

    def delete_flow(self, f):
        self.state.delete_flow(f)
        signals.flowlist_change.send(self)

    def refresh_focus(self):
        if self.state.view:
            signals.flow_change.send(
                self,
                flow = self.state.view[self.state.focus]
            )

    def process_flow(self, f):
        should_intercept = any(
            [
                self.state.intercept and f.match(self.state.intercept) and not f.request.is_replay,
                f.intercepted,
            ]
        )
        if should_intercept:
            f.intercept(self)
        signals.flowlist_change.send(self)
        signals.flow_change.send(self, flow = f)

    def clear_events(self):
        self.logbuffer[:] = []

    # Handlers
    @controller.handler
    def error(self, f):
        f = flow.FlowMaster.error(self, f)
        if f:
            self.process_flow(f)
        return f

    @controller.handler
    def request(self, f):
        f = flow.FlowMaster.request(self, f)
        if f:
            self.process_flow(f)
        return f

    @controller.handler
    def response(self, f):
        f = flow.FlowMaster.response(self, f)
        if f:
            self.process_flow(f)
        return f

    @controller.handler
    def tcp_message(self, f):
        super(ConsoleMaster, self).tcp_message(f)
        message = f.messages[-1]
        direction = "->" if message.from_client else "<-"
        self.add_log("{client} {direction} tcp {direction} {server}".format(
            client=repr(f.client_conn.address),
            server=repr(f.server_conn.address),
            direction=direction,
        ), "info")
        self.add_log(strutils.bytes_to_escaped_str(message.content), "debug")
