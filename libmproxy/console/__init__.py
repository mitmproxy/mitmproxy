from __future__ import absolute_import

import mailcap
import mimetypes
import tempfile
import os
import os.path
import shlex
import signal
import stat
import subprocess
import sys
import traceback
import urwid
import weakref

from .. import controller, flow, script
from . import flowlist, flowview, help, common, window, signals
from . import grideditor, palettes, contentview, flowdetailview, statusbar

EVENTLOG_SIZE = 500


class ConsoleState(flow.State):
    def __init__(self):
        flow.State.__init__(self)
        self.focus = None
        self.follow_focus = None
        self.default_body_view = contentview.get("Auto")

        self.view_mode = common.VIEW_LIST
        self.view_flow_mode = common.VIEW_FLOW_REQUEST

        self.last_script = ""
        self.last_saveload = ""
        self.flowsettings = weakref.WeakKeyDictionary()

    def add_flow_setting(self, flow, key, value):
        d = self.flowsettings.setdefault(flow, {})
        d[key] = value

    def get_flow_setting(self, flow, key, default=None):
        d = self.flowsettings.get(flow, {})
        return d.get(key, default)

    def add_flow(self, f):
        super(ConsoleState, self).add_flow(f)
        if self.focus is None:
            self.set_focus(0)
        elif self.follow_focus:
            self.set_focus(len(self.view) - 1)
        return f

    def update_flow(self, f):
        super(ConsoleState, self).update_flow(f)
        if self.focus is None:
            self.set_focus(0)
        return f

    def set_limit(self, limit):
        ret = flow.State.set_limit(self, limit)
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

    def set_focus_flow(self, f):
        self.set_focus(self.view.index(f))

    def get_from_pos(self, pos):
        if len(self.view) <= pos or pos < 0:
            return None, None
        return self.view[pos], pos

    def get_next(self, pos):
        return self.get_from_pos(pos+1)

    def get_prev(self, pos):
        return self.get_from_pos(pos-1)

    def delete_flow(self, f):
        if f in self.view and self.view.index(f) <= self.focus:
            self.focus -= 1
        if self.focus < 0:
            self.focus = None
        ret = flow.State.delete_flow(self, f)
        self.set_focus(self.focus)
        return ret

    def clear(self):
        self.focus = None
        super(ConsoleState, self).clear()


class Options(object):
    attributes = [
        "app",
        "app_domain",
        "app_ip",
        "anticache",
        "anticomp",
        "client_replay",
        "eventlog",
        "keepserving",
        "kill",
        "intercept",
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
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)


class ConsoleMaster(flow.FlowMaster):
    palette = []

    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, server, ConsoleState())
        self.stream_path = None
        self.options = options

        for i in options.replacements:
            self.replacehooks.add(*i)

        for i in options.setheaders:
            self.setheaders.add(*i)

        self.flow_list_walker = None
        self.set_palette(options.palette)

        r = self.set_intercept(options.intercept)
        if r:
            print >> sys.stderr, "Intercept error:", r
            sys.exit(1)

        r = self.set_stickycookie(options.stickycookie)
        if r:
            print >> sys.stderr, "Sticky cookies error:", r
            sys.exit(1)

        r = self.set_stickyauth(options.stickyauth)
        if r:
            print >> sys.stderr, "Sticky auth error:", r
            sys.exit(1)

        self.set_stream_large_bodies(options.stream_large_bodies)

        self.refresh_server_playback = options.refresh_server_playback
        self.anticache = options.anticache
        self.anticomp = options.anticomp
        self.killextra = options.kill
        self.rheaders = options.rheaders
        self.nopop = options.nopop
        self.showhost = options.showhost

        self.eventlog = options.eventlog
        self.eventlist = urwid.SimpleListWalker([])

        self.statusbar = None

        if options.client_replay:
            self.client_playback_path(options.client_replay)

        if options.server_replay:
            self.server_playback_path(options.server_replay)

        if options.scripts:
            for i in options.scripts:
                err = self.load_script(i)
                if err:
                    print >> sys.stderr, "Script load error:", err
                    sys.exit(1)

        if options.outfile:
            err = self.start_stream_to_path(
                options.outfile[0],
                options.outfile[1]
            )
            if err:
                print >> sys.stderr, "Stream file error:", err
                sys.exit(1)

        if options.app:
            self.start_app(self.options.app_host, self.options.app_port)
        signals.call_in.connect(self.sig_call_in)

    def sig_call_in(self, sender, seconds, callback, args=()):
        def cb(*_):
            return callback(*args)
        self.loop.set_alarm_in(seconds, cb)

    def start_stream_to_path(self, path, mode="wb"):
        path = os.path.expanduser(path)
        try:
            f = file(path, mode)
            self.start_stream(f, None)
        except IOError, v:
            return str(v)
        self.stream_path = path

    def _run_script_method(self, method, s, f):
        status, val = s.run(method, f)
        if val:
            if status:
                self.add_event("Method %s return: %s"%(method, val), "debug")
            else:
                self.add_event("Method %s error: %s"%(method, val[1]), "error")

    def run_script_once(self, command, f):
        if not command:
            return
        self.add_event("Running script on flow: %s"%command, "debug")

        try:
            s = script.Script(command, self)
        except script.ScriptError, v:
            signals.status_message.send(
                message = "Error loading script."
            )
            self.add_event("Error loading script:\n%s"%v.args[0], "error")
            return

        if f.request:
            self._run_script_method("request", s, f)
        if f.response:
            self._run_script_method("response", s, f)
        if f.error:
            self._run_script_method("error", s, f)
        s.unload()
        self.refresh_flow(f)
        self.state.last_script = command

    def set_script(self, command):
        if not command:
            return
        ret = self.load_script(command)
        if ret:
            signals.status_message.send(message=ret)
        self.state.last_script = command

    def toggle_eventlog(self):
        self.eventlog = not self.eventlog
        self.view_flowlist()

    def _readflow(self, paths):
        """
        Utitility function that reads a list of flows
        or prints an error to the UI if that fails.
        Returns
            - None, if there was an error.
            - a list of flows, otherwise.
        """
        try:
            return flow.read_flows_from_paths(paths)
        except flow.FlowReadError as e:
            if not self.statusbar:
                print >> sys.stderr, e.strerror
                sys.exit(1)
            else:
                signals.status_message.send(message=e.strerror)
            return None

    def client_playback_path(self, path):
        flows = self._readflow(path)
        if flows:
            self.start_client_playback(flows, False)

    def server_playback_path(self, path):
        flows = self._readflow(path)
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
            signals.status_message.send(message="Can't start editor: %s" % " ".join(c))
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
        self.palette = palettes.palettes[name]

    def ticker(self, *userdata):
        changed = self.tick(self.masterq, timeout=0)
        if changed:
            self.loop.draw_screen()
            self.statusbar.redraw()
        self.loop.set_alarm_in(0.01, self.ticker)

    def run(self):
        self.ui = urwid.raw_display.Screen()
        self.ui.set_terminal_properties(256)
        self.ui.register_palette(self.palette.palette())
        self.flow_list_walker = flowlist.FlowListWalker(self, self.state)
        self.view = None
        self.statusbar = None
        self.header = None
        self.body = None
        self.help_context = None
        self.prompting = False
        self.onekey = False
        self.loop = urwid.MainLoop(
            self.view,
            screen = self.ui,
        )
        self.view_flowlist()
        self.statusbar.redraw()

        self.server.start_slave(
            controller.Slave,
            controller.Channel(self.masterq, self.should_exit)
        )

        if self.options.rfile:
            ret = self.load_flows_path(self.options.rfile)
            if ret and self.state.flow_count():
                self.add_event(
                    "File truncated or corrupted. "
                    "Loaded as many flows as possible.",
                    "error"
                )
            elif ret and not self.state.flow_count():
                self.shutdown()
                print >> sys.stderr, "Could not load file:", ret
                sys.exit(1)

        self.loop.set_alarm_in(0.01, self.ticker)

        # It's not clear why we need to handle this explicitly - without this,
        # mitmproxy hangs on keyboard interrupt. Remove if we ever figure it
        # out.
        def exit(s, f):
            raise urwid.ExitMainLoop
        signal.signal(signal.SIGINT, exit)

        try:
            self.loop.run()
        except Exception:
            self.loop.stop()
            sys.stdout.flush()
            print >> sys.stderr, traceback.format_exc()
            print >> sys.stderr, "mitmproxy has crashed!"
            print >> sys.stderr, "Please lodge a bug report at:"
            print >> sys.stderr, "\thttps://github.com/mitmproxy/mitmproxy"
            print >> sys.stderr, "Shutting down..."
        sys.stderr.flush()
        self.shutdown()

    def make_view(self):
        self.view = window.Window(
            self,
            self.body,
            header = self.header,
            footer = self.statusbar
        )
        self.statusbar.redraw()
        return self.view

    def view_help(self):
        h = help.HelpView(
            self,
            self.help_context,
            (self.statusbar, self.body, self.header)
        )
        self.statusbar = statusbar.StatusBar(self, help.footer)
        self.body = h
        self.header = None
        self.loop.widget = self.make_view()

    def view_flowdetails(self, flow):
        h = flowdetailview.FlowDetailsView(
            self,
            flow,
            (self.statusbar, self.body, self.header)
        )
        self.statusbar = statusbar.StatusBar(self, flowdetailview.footer)
        self.body = h
        self.header = None
        self.loop.widget = self.make_view()

    def view_grideditor(self, ge):
        self.body = ge
        self.header = None
        self.help_context = ge.make_help()
        self.statusbar = statusbar.StatusBar(self, grideditor.footer)
        self.loop.widget = self.make_view()

    def view_flowlist(self):
        if self.ui.started:
            self.ui.clear()
        if self.state.follow_focus:
            self.state.set_focus(self.state.flow_count())

        if self.eventlog:
            self.body = flowlist.BodyPile(self)
        else:
            self.body = flowlist.FlowListBox(self)
        self.statusbar = statusbar.StatusBar(self, flowlist.footer)
        self.header = None
        self.state.view_mode = common.VIEW_LIST

        self.loop.widget = self.make_view()
        self.help_context = flowlist.help_context

    def view_flow(self, flow):
        self.body = flowview.FlowView(self, self.state, flow)
        self.header = flowview.FlowViewHeader(self, flow)
        self.statusbar = statusbar.StatusBar(self, flowview.footer)
        self.state.set_focus_flow(flow)
        self.state.view_mode = common.VIEW_FLOW
        self.loop.widget = self.make_view()
        self.help_context = flowview.help_context

    def _write_flows(self, path, flows):
        self.state.last_saveload = path
        if not path:
            return
        path = os.path.expanduser(path)
        try:
            f = file(path, "wb")
            fw = flow.FlowWriter(f)
            for i in flows:
                fw.add(i)
            f.close()
        except IOError, v:
            signals.status_message.send(message=v.strerror)

    def save_one_flow(self, path, flow):
        return self._write_flows(path, [flow])

    def save_flows(self, path):
        return self._write_flows(path, self.state.view)

    def load_flows_callback(self, path):
        if not path:
            return
        ret = self.load_flows_path(path)
        return ret or "Flows loaded from %s"%path

    def load_flows_path(self, path):
        self.state.last_saveload = path
        reterr = None
        try:
            flow.FlowMaster.load_flows_file(self, path)
        except flow.FlowReadError, v:
            reterr = str(v)
        if self.flow_list_walker:
            self.sync_list_view()
        return reterr

    def path_prompt(self, prompt, text, callback, *args):
        self.statusbar.path_prompt(prompt, text)
        self.view.set_focus("footer")
        self.prompting = (callback, args)

    def prompt(self, prompt, text, callback, *args):
        self.statusbar.prompt(prompt, text)
        self.view.set_focus("footer")
        self.prompting = (callback, args)

    def prompt_edit(self, prompt, text, callback):
        self.statusbar.prompt(prompt + ": ", text)
        self.view.set_focus("footer")
        self.prompting = (callback, [])

    def prompt_onekey(self, prompt, keys, callback, *args):
        """
            Keys are a set of (word, key) tuples. The appropriate key in the
            word is highlighted.
        """
        prompt = [prompt, " ("]
        mkup = []
        for i, e in enumerate(keys):
            mkup.extend(common.highlight_key(e[0], e[1]))
            if i < len(keys)-1:
                mkup.append(",")
        prompt.extend(mkup)
        prompt.append(")? ")
        self.onekey = set(i[1] for i in keys)
        self.prompt(prompt, "", callback, *args)

    def prompt_done(self):
        self.prompting = False
        self.onekey = False
        self.view.set_focus("body")
        signals.status_message.send(message="")

    def prompt_execute(self, txt=None):
        if not txt:
            txt = self.statusbar.get_edit_text()
        p, args = self.prompting
        self.prompt_done()
        msg = p(txt, *args)
        if msg:
            signals.status_message.send(message=msg, expire=1)

    def prompt_cancel(self):
        self.prompt_done()

    def accept_all(self):
        self.state.accept_all(self)

    def set_limit(self, txt):
        v = self.state.set_limit(txt)
        self.sync_list_view()
        return v

    def set_intercept(self, txt):
        return self.state.set_intercept(txt)

    def change_default_display_mode(self, t):
        v = contentview.get_by_shortcut(t)
        self.state.default_body_view = v
        self.refresh_focus()

    def pop_view(self):
        if self.state.view_mode == common.VIEW_FLOW:
            self.view_flow(self.state.view[self.state.focus])
        else:
            self.view_flowlist()

    def edit_scripts(self, scripts):
        commands = [x[0] for x in scripts]  # remove outer array
        if commands == [s.command for s in self.scripts]:
            return

        self.unload_scripts()
        for command in commands:
            self.load_script(command)

    def edit_ignore_filter(self, ignore):
        patterns = (x[0] for x in ignore)
        self.set_ignore_filter(patterns)

    def edit_tcp_filter(self, tcp):
        patterns = (x[0] for x in tcp)
        self.set_tcp_filter(patterns)

    def stop_client_playback_prompt(self, a):
        if a != "n":
            self.stop_client_playback()

    def stop_server_playback_prompt(self, a):
        if a != "n":
            self.stop_server_playback()

    def quit(self, a):
        if a != "n":
            raise urwid.ExitMainLoop

    def _change_options(self, a):
        if a == "a":
            self.anticache = not self.anticache
        if a == "c":
            self.anticomp = not self.anticomp
        if a == "h":
            self.showhost = not self.showhost
            self.sync_list_view()
            self.refresh_focus()
        elif a == "k":
            self.killextra = not self.killextra
        elif a == "n":
            self.refresh_server_playback = not self.refresh_server_playback
        elif a == "u":
            self.server.config.no_upstream_cert =\
                not self.server.config.no_upstream_cert

    def shutdown(self):
        self.state.killall(self)
        flow.FlowMaster.shutdown(self)

    def sync_list_view(self):
        self.flow_list_walker._modified()

    def clear_flows(self):
        self.state.clear()
        self.sync_list_view()

    def toggle_follow_flows(self):
        # toggle flow follow
        self.state.follow_focus = not self.state.follow_focus
        # jump to most recent flow if follow is now on
        if self.state.follow_focus:
            self.state.set_focus(self.state.flow_count())
            self.sync_list_view()

    def delete_flow(self, f):
        self.state.delete_flow(f)
        self.sync_list_view()

    def refresh_focus(self):
        if self.state.view:
            self.refresh_flow(self.state.view[self.state.focus])

    def refresh_flow(self, c):
        if hasattr(self.header, "refresh_flow"):
            self.header.refresh_flow(c)
        if hasattr(self.body, "refresh_flow"):
            self.body.refresh_flow(c)
        if hasattr(self.statusbar, "refresh_flow"):
            self.statusbar.refresh_flow(c)

    def process_flow(self, f):
        if self.state.intercept and f.match(self.state.intercept) and not f.request.is_replay:
            f.intercept(self)
        else:
            f.reply()
        self.sync_list_view()
        self.refresh_flow(f)

    def clear_events(self):
        self.eventlist[:] = []

    def add_event(self, e, level="info"):
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
        self.eventlist.set_focus(len(self.eventlist)-1)

    # Handlers
    def handle_error(self, f):
        f = flow.FlowMaster.handle_error(self, f)
        if f:
            self.process_flow(f)
        return f

    def handle_request(self, f):
        f = flow.FlowMaster.handle_request(self, f)
        if f:
            self.process_flow(f)
        return f

    def handle_response(self, f):
        f = flow.FlowMaster.handle_response(self, f)
        if f:
            self.process_flow(f)
        return f
