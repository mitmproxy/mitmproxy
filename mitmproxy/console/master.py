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

import urwid

from mitmproxy import builtins
from mitmproxy import contentviews
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import script
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
        self.last_filter = None
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
        self.set_flow_marked(f, False)
        return f

    def update_flow(self, f):
        super(ConsoleState, self).update_flow(f)
        self.update_focus()
        return f

    def set_limit(self, limit):
        ret = super(ConsoleState, self).set_limit(limit)
        self.set_focus(self.focus)
        return ret

    def get_focus(self):
        if not self.view or self.focus is None:
            return None, None
        return self.view[self.focus], self.focus

    def set_focus(self, idx):
        if self.view:
            if idx >= len(self.view):
                idx = len(self.view) - 1
            elif idx < 0:
                idx = 0
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

    def filter_marked(self, m):
        def actual_func(x):
            if x.id in m:
                return True
            return False
        return actual_func

    def enable_marked_filter(self):
        self.last_filter = self.limit_txt
        marked_flows = []
        for f in self.flows:
            if self.flow_marked(f):
                marked_flows.append(f.id)
        if len(marked_flows) > 0:
            f = self.filter_marked(marked_flows)
            self.view._close()
            self.view = flow.FlowView(self.flows, f)
            self.focus = 0
            self.set_focus(self.focus)
            self.mark_filter = True

    def disable_marked_filter(self):
        if self.last_filter is None:
            self.view = flow.FlowView(self.flows, None)
        else:
            self.set_limit(self.last_filter)
        self.focus = 0
        self.set_focus(self.focus)
        self.last_filter = None
        self.mark_filter = False

    def clear(self):
        marked_flows = []
        for f in self.flows:
            if self.flow_marked(f):
                marked_flows.append(f)

        super(ConsoleState, self).clear()

        for f in marked_flows:
            self.add_flow(f)
            self.set_flow_marked(f, True)

        if len(self.flows.views) == 0:
            self.focus = None
        else:
            self.focus = 0
        self.set_focus(self.focus)

    def flow_marked(self, flow):
        return self.get_flow_setting(flow, "marked", False)

    def set_flow_marked(self, flow, marked):
        self.add_flow_setting(flow, "marked", marked)


class Options(mitmproxy.options.Options):
    attributes = [
        "app",
        "app_domain",
        "app_ip",
        "anticache",
        "anticomp",
        "client_replay",
        "eventlog",
        "follow",
        "keepserving",
        "kill",
        "intercept",
        "limit",
        "no_server",
        "refresh_server_playback",
        "rfile",
        "scripts",
        "showhost",
        "replacements",
        "rheaders",
        "setheaders",
        "server_replay",
        "stickycookie",
        "stickyauth",
        "stream_large_bodies",
        "verbosity",
        "wfile",
        "nopop",
        "palette",
        "palette_transparent",
        "no_mouse",
        "outfile",
    ]


class ConsoleMaster(flow.FlowMaster):
    palette = []

    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, options, server, ConsoleState())
        self.addons.add(*builtins.default_addons())

        self.stream_path = None
        self.options.errored.connect(self.options_error)

        if options.replacements:
            for i in options.replacements:
                self.replacehooks.add(*i)

        if options.setheaders:
            for i in options.setheaders:
                self.setheaders.add(*i)

        r = self.set_intercept(options.intercept)
        if r:
            print("Intercept error: {}".format(r), file=sys.stderr)
            sys.exit(1)

        if options.limit:
            self.set_limit(options.limit)

        self.set_stream_large_bodies(options.stream_large_bodies)

        self.refresh_server_playback = options.refresh_server_playback
        self.anticache = options.anticache
        self.killextra = options.kill
        self.rheaders = options.rheaders
        self.nopop = options.nopop
        self.showhost = options.showhost
        self.palette = options.palette
        self.palette_transparent = options.palette_transparent

        self.eventlog = options.eventlog
        self.eventlist = urwid.SimpleListWalker([])
        self.follow = options.follow

        if options.client_replay:
            self.client_playback_path(options.client_replay)

        if options.server_replay:
            self.server_playback_path(options.server_replay)

        if options.scripts:
            for i in options.scripts:
                try:
                    self.load_script(i)
                except exceptions.ScriptException as e:
                    print("Script load error: {}".format(e), file=sys.stderr)
                    sys.exit(1)

        if options.outfile:
            err = self.start_stream_to_path(
                options.outfile[0],
                options.outfile[1]
            )
            if err:
                print("Stream file error: {}".format(err), file=sys.stderr)
                sys.exit(1)

        self.view_stack = []

        if options.app:
            self.start_app(self.options.app_host, self.options.app_port)
        signals.call_in.connect(self.sig_call_in)
        signals.pop_view_state.connect(self.sig_pop_view_state)
        signals.push_view_state.connect(self.sig_push_view_state)
        signals.sig_add_event.connect(self.sig_add_event)

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        signals.update_settings.send(self)

    def options_error(self, opts, exc):
        signals.status_message.send(
            message=str(exc),
            expire=1
        )

    def load_script(self, command, use_reloader=True):
        # We default to using the reloader in the console ui.
        return super(ConsoleMaster, self).load_script(command, use_reloader)

    def sig_add_event(self, sender, e, level):
        needed = dict(error=0, info=1, debug=2).get(level, 1)
        if self.options.verbosity < needed:
            return

        if level == "error":
            e = urwid.Text(("error", str(e)))
        else:
            e = urwid.Text(str(e))
        self.eventlist.append(e)
        if len(self.eventlist) > EVENTLOG_SIZE:
            self.eventlist.pop(0)
        self.eventlist.set_focus(len(self.eventlist) - 1)

    def add_event(self, e, level):
        signals.add_event(e, level)

    def sig_call_in(self, sender, seconds, callback, args=()):
        def cb(*_):
            return callback(*args)
        self.loop.set_alarm_in(seconds, cb)

    def sig_pop_view_state(self, sender):
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
        self.view_stack.append(window)
        self.loop.widget = window
        self.loop.draw_screen()

    def _run_script_method(self, method, s, f):
        status, val = s.run(method, f)
        if val:
            if status:
                signals.add_event("Method %s return: %s" % (method, val), "debug")
            else:
                signals.add_event(
                    "Method %s error: %s" %
                    (method, val[1]), "error")

    def run_script_once(self, command, f):
        if not command:
            return
        signals.add_event("Running script on flow: %s" % command, "debug")

        try:
            s = script.Script(command)
            s.load()
        except script.ScriptException as e:
            signals.status_message.send(
                message='Error loading "{}".'.format(command)
            )
            signals.add_event('Error loading "{}":\n{}'.format(command, e), "error")
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
        self.eventlog = not self.eventlog
        signals.pop_view_state.send(self)
        self.view_flowlist()

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
            signals.status_message.send(message=e.strerror)

    def client_playback_path(self, path):
        if not isinstance(path, list):
            path = [path]
        flows = self._readflows(path)
        if flows:
            self.start_client_playback(flows, False)

    def server_playback_path(self, path):
        if not isinstance(path, list):
            path = [path]
        flows = self._readflows(path)
        if flows:
            self.start_server_playback(
                flows,
                self.killextra, self.rheaders,
                False, self.nopop,
                self.options.replay_ignore_params,
                self.options.replay_ignore_content,
                self.options.replay_ignore_payload_params,
                self.options.replay_ignore_host
            )

    def spawn_editor(self, data):
        fd, name = tempfile.mkstemp('', "mproxy")
        os.write(fd, data)
        os.close(fd)
        c = os.environ.get("EDITOR")
        # if no EDITOR is set, assume 'vi'
        if not c:
            c = "vi"
        cmd = shlex.split(c)
        cmd.append(name)
        self.ui.stop()
        try:
            subprocess.call(cmd)
        except:
            signals.status_message.send(
                message = "Can't start editor: %s" % " ".join(c)
            )
        else:
            data = open(name, "rb").read()
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

        if self.options.rfile:
            ret = self.load_flows_path(self.options.rfile)
            if ret and self.state.flow_count():
                signals.add_event(
                    "File truncated or corrupted. "
                    "Loaded as many flows as possible.",
                    "error"
                )
            elif ret and not self.state.flow_count():
                self.shutdown()
                print("Could not load file: {}".format(ret), file=sys.stderr)
                sys.exit(1)

        self.loop.set_alarm_in(0.01, self.ticker)
        if self.server.config.http2 and not tcp.HAS_ALPN:  # pragma: no cover
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
                statusbar.StatusBar(self, grideditor.FOOTER),
                ge.make_help()
            )
        )

    def view_flowlist(self):
        if self.ui.started:
            self.ui.clear()
        if self.state.follow_focus:
            self.state.set_focus(self.state.flow_count())

        if self.eventlog:
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
            f = file(path, "wb")
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

    def save_marked_flows(self, path):
        marked_flows = []
        for f in self.state.view:
            if self.state.flow_marked(f):
                marked_flows.append(f)
        return self._write_flows(path, marked_flows)

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

    def set_limit(self, txt):
        v = self.state.set_limit(txt)
        signals.flowlist_change.send(self)
        return v

    def set_intercept(self, txt):
        return self.state.set_intercept(txt)

    def change_default_display_mode(self, t):
        v = contentviews.get_by_shortcut(t)
        self.state.default_body_view = v
        self.refresh_focus()

    def edit_scripts(self, scripts):
        commands = [x[0] for x in scripts]  # remove outer array
        if commands == [s.command for s in self.scripts]:
            return

        self.unload_scripts()
        for command in commands:
            try:
                self.load_script(command)
            except exceptions.ScriptException as e:
                signals.status_message.send(
                    message='Error loading "{}".'.format(command)
                )
                signals.add_event('Error loading "{}":\n{}'.format(command, e), "error")
        signals.update_settings.send(self)

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
            f.reply.take()
        signals.flowlist_change.send(self)
        signals.flow_change.send(self, flow = f)

    def clear_events(self):
        self.eventlist[:] = []

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
        self.add_event("{client} {direction} tcp {direction} {server}".format(
            client=repr(f.client_conn.address),
            server=repr(f.server_conn.address),
            direction=direction,
        ), "info")
        self.add_event(strutils.bytes_to_escaped_str(message.content), "debug")

    @controller.handler
    def script_change(self, script):
        if super(ConsoleMaster, self).script_change(script):
            signals.status_message.send(message='"{}" reloaded.'.format(script.path))
        else:
            signals.status_message.send(message='Error reloading "{}".'.format(script.path))
