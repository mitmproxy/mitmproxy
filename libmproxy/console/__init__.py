# Copyright (C) 2010  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import mailcap, mimetypes, tempfile, os, subprocess, glob, time, re
import os.path, sys
import cStringIO
import urwid
from .. import controller, utils, filt, flow
import connlist, connview, help, common, kveditor

EVENTLOG_SIZE = 500


class Stop(Exception): pass


#begin nocover


class _PathCompleter:
    def __init__(self, _testing=False):
        """
            _testing: disables reloading of the lookup table to make testing possible.
        """
        self.lookup, self.offset = None, None
        self.final = None
        self._testing = _testing

    def reset(self):
        self.lookup = None
        self.offset = -1

    def complete(self, txt):
        """
            Returns the next completion for txt, or None if there is no completion.
        """
        path = os.path.expanduser(txt)
        if not self.lookup:
            if not self._testing:
                # Lookup is a set of (display value, actual value) tuples.
                self.lookup = []
                if os.path.isdir(path):
                    files = glob.glob(os.path.join(path, "*"))
                    prefix = txt
                else:
                    files = glob.glob(path+"*")
                    prefix = os.path.dirname(txt)
                prefix = prefix or "./"
                for f in files:
                    display = os.path.join(prefix, os.path.basename(f))
                    if os.path.isdir(f):
                        display += "/"
                    self.lookup.append((display, f))
            if not self.lookup:
                self.final = path
                return path
            self.lookup.sort()
            self.offset = -1
            self.lookup.append((txt, txt))
        self.offset += 1
        if self.offset >= len(self.lookup):
            self.offset = 0
        ret = self.lookup[self.offset]
        self.final = ret[1]
        return ret[0]


class PathEdit(urwid.Edit, _PathCompleter):
    def __init__(self, *args, **kwargs):
        urwid.Edit.__init__(self, *args, **kwargs)
        _PathCompleter.__init__(self)

    def keypress(self, size, key):
        if key == "tab":
            comp = self.complete(self.get_edit_text())
            self.set_edit_text(comp)
            self.set_edit_pos(len(comp))
        else:
            self.reset()
        return urwid.Edit.keypress(self, size, key)


class ActionBar(common.WWrap):
    def __init__(self):
        self.message("")

    def selectable(self):
        return True

    def path_prompt(self, prompt, text):
        self.w = PathEdit(prompt, text)

    def prompt(self, prompt, text = ""):
        self.w = urwid.Edit(prompt, text or "")

    def message(self, message):
        self.w = urwid.Text(message)


class StatusBar(common.WWrap):
    def __init__(self, master, helptext):
        self.master, self.helptext = master, helptext
        self.expire = None
        self.ab = ActionBar()
        self.ib = common.WWrap(urwid.Text(""))
        self.w = urwid.Pile([self.ib, self.ab])

    def get_status(self):
        r = []

        if self.master.client_playback:
            r.append("[")
            r.append(("statusbar_highlight", "cplayback"))
            r.append(":%s to go]"%self.master.client_playback.count())
        if self.master.server_playback:
            r.append("[")
            r.append(("statusbar_highlight", "splayback"))
            r.append(":%s to go]"%self.master.server_playback.count())
        if self.master.state.intercept_txt:
            r.append("[")
            r.append(("statusbar_highlight", "i"))
            r.append(":%s]"%self.master.state.intercept_txt)
        if self.master.state.limit_txt:
            r.append("[")
            r.append(("statusbar_highlight", "l"))
            r.append(":%s]"%self.master.state.limit_txt)
        if self.master.stickycookie_txt:
            r.append("[")
            r.append(("statusbar_highlight", "t"))
            r.append(":%s]"%self.master.stickycookie_txt)
        if self.master.stickyauth_txt:
            r.append("[")
            r.append(("statusbar_highlight", "u"))
            r.append(":%s]"%self.master.stickyauth_txt)

        opts = []
        if self.master.anticache:
            opts.append("anticache")
        if self.master.anticomp:
            opts.append("anticomp")
        if not self.master.refresh_server_playback:
            opts.append("norefresh")
        if self.master.killextra:
            opts.append("killextra")

        if opts:
            r.append("[%s]"%(":".join(opts)))

        if self.master.script:
            r.append("[script:%s]"%self.master.script.path)

        if self.master.debug:
            r.append("[lt:%0.3f]"%self.master.looptime)

        return r

    def redraw(self):
        if self.expire and time.time() > self.expire:
            self.message("")

        t = [
                ('statusbar_text', ("[%s]"%self.master.state.flow_count()).ljust(7)),
            ]
        t.extend(self.get_status())

        if self.master.server:
            boundaddr = "[%s:%s]"%(self.master.server.address or "*", self.master.server.port)
        else:
            boundaddr = ""

        status = urwid.AttrWrap(urwid.Columns([
            urwid.Text(t),
            urwid.Text(
                [
                    self.helptext,
                    " ",
                    ('statusbar_text', "["),
                    ('statusbar_key', "m"),
                    ('statusbar_text', (":%s]"%common.BODY_VIEWS[self.master.state.view_body_mode])),
                    ('statusbar_text', boundaddr),
                ],
                align="right"
            ),
        ]), "statusbar")
        self.ib.set_w(status)

    def update(self, text):
        self.helptext = text
        self.redraw()
        self.master.drawscreen()

    def selectable(self):
        return True

    def get_edit_text(self):
        return self.ab.w.get_edit_text()

    def path_prompt(self, prompt, text):
        return self.ab.path_prompt(prompt, text)

    def prompt(self, prompt, text = ""):
        self.ab.prompt(prompt, text)

    def message(self, msg, expire=None):
        if expire:
            self.expire = time.time() + float(expire)/1000
        else:
            self.expire = None
        self.ab.message(msg)


#end nocover

class ConsoleState(flow.State):
    def __init__(self):
        flow.State.__init__(self)
        self.focus = None
        self.view_body_mode = common.VIEW_BODY_PRETTY
        self.view_flow_mode = common.VIEW_FLOW_REQUEST
        self.last_script = ""
        self.last_saveload = ""

    def add_request(self, req):
        f = flow.State.add_request(self, req)
        if self.focus is None:
            self.set_focus(0)
        return f

    def add_response(self, resp):
        f = flow.State.add_response(self, resp)
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

    def get_from_pos(self, pos):
        if len(self.view) <= pos or pos < 0:
            return None, None
        return self.view[pos], pos

    def get_next(self, pos):
        return self.get_from_pos(pos+1)

    def get_prev(self, pos):
        return self.get_from_pos(pos-1)

    def delete_flow(self, f):
        ret = flow.State.delete_flow(self, f)
        self.set_focus(self.focus)
        return ret



class Options(object):
    __slots__ = [
        "anticache",
        "anticomp",
        "client_replay",
        "debug",
        "eventlog",
        "keepserving",
        "kill",
        "intercept",
        "no_server",
        "refresh_server_playback",
        "rfile",
        "script",
        "rheaders",
        "server_replay",
        "stickycookie",
        "stickyauth",
        "verbosity",
        "wfile",
    ]
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.__slots__:
            if not hasattr(self, i):
                setattr(self, i, None)


#begin nocover


class ConsoleMaster(flow.FlowMaster):
    palette = []
    footer_text_default = [
        ('statusbar_key', "?"), ":help ",
    ]
    footer_text_help = [
        ('statusbar_key', "q"), ":back",
    ]
    footer_text_connview = [
        ('statusbar_key', "tab"), ":toggle view ",
        ('statusbar_key', "?"), ":help ",
        ('statusbar_key', "q"), ":back ",
    ]
    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, server, ConsoleState())
        self.looptime = 0
        self.options = options

        self.conn_list_view = None
        self.set_palette()

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

        self.refresh_server_playback = options.refresh_server_playback
        self.anticache = options.anticache
        self.anticomp = options.anticomp
        self.killextra = options.kill
        self.rheaders = options.rheaders

        self.eventlog = options.eventlog
        self.eventlist = urwid.SimpleListWalker([])

        if options.client_replay:
            self.client_playback_path(options.client_replay)

        if options.server_replay:
            self.server_playback_path(options.server_replay)

        self.debug = options.debug

        if options.script:
            err = self.load_script(options.script)
            if err:
                print >> sys.stderr, "Script load error:", err
                sys.exit(1)

    def run_script_once(self, path, f):
        ret = self.get_script(path)
        if ret[0]:
            self.statusbar.message(ret[0])
        s = ret[1]

        if f.request:
            s.run("request", f)
        if f.response:
            s.run("response", f)
        if f.error:
            s.run("error", f)
        s.run("done")
        self.refresh_connection(f)
        self.state.last_script = path

    def set_script(self, path):
        if not path:
            return
        ret = self.load_script(path)
        if ret:
            self.statusbar.message(ret)
        self.state.last_script = path

    def toggle_eventlog(self):
        self.eventlog = not self.eventlog
        self.view_connlist()

    def _readflow(self, path):
        path = os.path.expanduser(path)
        try:
            f = file(path, "r")
            flows = list(flow.FlowReader(f).stream())
        except (IOError, flow.FlowReadError), v:
            return True, v.strerror
        return False, flows

    def client_playback_path(self, path):
        err, ret = self._readflow(path)
        if err:
            self.statusbar.message(ret)
        else:
            self.start_client_playback(ret, False)

    def server_playback_path(self, path):
        err, ret = self._readflow(path)
        if err:
            self.statusbar.message(ret)
        else:
            self.start_server_playback(
                ret,
                self.killextra, self.rheaders,
                False
            )

    def spawn_external_viewer(self, data, contenttype):
        if contenttype:
            ext = mimetypes.guess_extension(contenttype) or ""
        else:
            ext = ""
        fd, name = tempfile.mkstemp(ext, "mproxy")
        os.write(fd, data)
        os.close(fd)

        cmd = None
        shell = False

        if contenttype:
            c = mailcap.getcaps()
            cmd, _ = mailcap.findmatch(c, contenttype, filename=name)
            if cmd:
                shell = True
        if not cmd:
            c = os.environ.get("PAGER") or os.environ.get("EDITOR")
            cmd = [c, name]
        self.ui.stop()
        subprocess.call(cmd, shell=shell)
        self.ui.start()
        os.unlink(name)

    def set_palette(self):
        BARBG = "dark blue"
        self.palette = [
            ('body', 'black', 'dark cyan', 'standout'),
            ('foot', 'light gray', 'default'),
            ('title', 'white,bold', 'default',),
            ('editline', 'white', 'default',),

            # Status bar
            ('statusbar', 'light gray', BARBG),
            ('statusbar_key', 'light cyan', BARBG),
            ('statusbar_text', 'light gray', BARBG),
            ('statusbar_highlight', 'white', BARBG),

            # Help
            ('key', 'light cyan', 'default', 'underline'),
            ('head', 'white,bold', 'default'),
            ('text', 'light gray', 'default'),

            # List and Connections
            ('method', 'dark cyan', 'default'),
            ('focus', 'yellow', 'default'),
            ('goodcode', 'light green', 'default'),
            ('error', 'light red', 'default'),
            ('header', 'dark cyan', 'default'),
            ('heading', 'white,bold', 'dark blue'),
            ('inactive_heading', 'white', 'dark gray'),
            ('highlight', 'white,bold', 'default'),
            ('inactive', 'dark gray', 'default'),
            ('ack', 'light red', 'default'),

            # Hex view
            ('offset', 'dark cyan', 'default'),

            # KV Editor
            ('editfield', 'black', 'light cyan'),
        ]

    def run(self):
        self.currentflow = None

        self.ui = urwid.raw_display.Screen()
        self.ui.register_palette(self.palette)
        self.conn_list_view = connlist.ConnectionListView(self, self.state)

        self.view = None
        self.statusbar = None
        self.header = None
        self.body = None

        self.prompting = False
        self.onekey = False
        self.view_connlist()

        if self.server:
            slave = controller.Slave(self.masterq, self.server)
            slave.start()

        if self.options.rfile:
            ret = self.load_flows(self.options.rfile)
            if ret:
                self.shutdown()
                print >> sys.stderr, "Could not load file:", ret
                sys.exit(1)

        self.ui.run_wrapper(self.loop)
        # If True, quit just pops out to connection list view.
        print >> sys.stderr, "Shutting down..."
        sys.stderr.flush()
        self.shutdown()

    def make_view(self):
        self.view = urwid.Frame(
                        self.body,
                        header = self.header,
                        footer = self.statusbar
                    )
        self.view.set_focus("body")

    def view_help(self):
        self.statusbar = StatusBar(self, self.footer_text_help)
        self.body = help.HelpView(self)
        self.header = None
        self.make_view()

    def view_kveditor(self, title, value, callback):
        self.statusbar = StatusBar(self, "foo")
        self.body = kveditor.KVEditor(self, title, value, callback)
        self.header = None
        self.make_view()

    def focus_current(self):
        if self.currentflow:
            try:
                ids = [id(i) for i in self.state.view]
                idx = ids.index(id(self.currentflow))
                self.conn_list_view.set_focus(idx)
            except (IndexError, ValueError):
                pass

    def view_connlist(self):
        if self.ui.started:
            self.ui.clear()
        self.focus_current()
        if self.eventlog:
            self.body = connlist.BodyPile(self)
        else:
            self.body = connlist.ConnectionListBox(self)
        self.statusbar = StatusBar(self, self.footer_text_default)
        self.header = None
        self.currentflow = None
        self.make_view()

    def view_flow(self, flow):
        self.statusbar = StatusBar(self, self.footer_text_connview)
        self.body = connview.ConnectionView(self, self.state, flow)
        self.header = connview.ConnectionViewHeader(self, flow)
        self.currentflow = flow
        self.make_view()

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
            self.statusbar.message(v.strerror)

    def save_one_flow(self, path, flow):
        return self._write_flows(path, [flow])

    def save_flows(self, path):
        return self._write_flows(path, self.state.view)

    def load_flows_callback(self, path):
        if not path:
            return
        ret = self.load_flows(path)
        return ret or "Flows loaded from %s"%path

    def load_flows(self, path):
        self.state.last_saveload = path
        path = os.path.expanduser(path)
        try:
            f = file(path, "r")
            fr = flow.FlowReader(f)
        except IOError, v:
            return v.strerror
        flow.FlowMaster.load_flows(self, fr)
        f.close()
        if self.conn_list_view:
            self.sync_list_view()
            self.focus_current()

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
        self.onekey = "".join(i[1] for i in keys)
        self.prompt(prompt, "", callback, *args)

    def prompt_done(self):
        self.prompting = False
        self.onekey = False
        self.view.set_focus("body")
        self.statusbar.message("")

    def prompt_execute(self, txt=None):
        if not txt:
            txt = self.statusbar.get_edit_text()
        p, args = self.prompting
        self.prompt_done()
        msg = p(txt, *args)
        if msg:
            self.statusbar.message(msg, 1000)

    def prompt_cancel(self):
        self.prompt_done()

    def accept_all(self):
        self.state.accept_all()

    def set_limit(self, txt):
        return self.state.set_limit(txt)

    def set_intercept(self, txt):
        return self.state.set_intercept(txt)

    def changeview(self, v):
        if v == "r":
            self.state.view_body_mode = common.VIEW_BODY_RAW
        elif v == "h":
            self.state.view_body_mode = common.VIEW_BODY_HEX
        elif v == "p":
            self.state.view_body_mode = common.VIEW_BODY_PRETTY
        self.refresh_connection(self.currentflow)

    def drawscreen(self):
        size = self.ui.get_cols_rows()
        canvas = self.view.render(size, focus=1)
        self.ui.draw_screen(size, canvas)
        return size

    def pop_view(self):
        if self.currentflow:
            self.view_flow(self.currentflow)
        else:
            self.view_connlist()

    def loop(self):
        changed = True
        try:
            while not controller.should_exit:
                startloop = time.time()
                if changed:
                    self.statusbar.redraw()
                    size = self.drawscreen()
                changed = self.tick(self.masterq)
                self.ui.set_input_timeouts(max_wait=0.1)
                keys = self.ui.get_input()
                if keys:
                    changed = True
                for k in keys:
                    if self.prompting:
                        if k == "esc":
                            self.prompt_cancel()
                        elif self.onekey:
                            if k == "enter":
                                self.prompt_cancel()
                            elif k in self.onekey:
                                self.prompt_execute(k)
                        elif k == "enter":
                            self.prompt_execute()
                        else:
                            self.view.keypress(size, k)
                    else:
                        k = self.view.keypress(size, k)
                        if k:
                            self.statusbar.message("")
                            if k == "?":
                                self.view_help()
                            elif k == "c":
                                if not self.client_playback:
                                    self.path_prompt(
                                        "Client replay: ",
                                        self.state.last_saveload,
                                        self.client_playback_path
                                    )
                                else:
                                    self.prompt_onekey(
                                        "Stop current client replay?",
                                        (
                                            ("yes", "y"),
                                            ("no", "n"),
                                        ),
                                        self.stop_client_playback_prompt,
                                    )
                            elif k == "l":
                                self.prompt("Limit: ", self.state.limit_txt, self.set_limit)
                                self.sync_list_view()
                            elif k == "i":
                                self.prompt(
                                    "Intercept filter: ",
                                    self.state.intercept_txt,
                                    self.set_intercept
                                )
                                self.sync_list_view()
                            elif k == "m":
                                self.prompt_onekey(
                                    "View",
                                    (
                                        ("raw", "r"),
                                        ("pretty", "p"),
                                        ("hex", "h"),
                                    ),
                                    self.changeview
                                )
                            elif k == "Q":
                                raise Stop
                            elif k == "q":
                                self.prompt_onekey(
                                    "Quit",
                                    (
                                        ("yes", "y"),
                                        ("no", "n"),
                                    ),
                                    self.quit,
                                )
                            elif k == "w":
                                self.path_prompt(
                                    "Save flows: ",
                                    self.state.last_saveload,
                                    self.save_flows
                                )
                            elif k == "s":
                                if self.script:
                                    self.load_script(None)
                                else:
                                    self.path_prompt(
                                        "Set script: ",
                                        self.state.last_script,
                                        self.set_script
                                    )
                            elif k == "S":
                                if not self.server_playback:
                                    self.path_prompt(
                                        "Server replay: ",
                                        self.state.last_saveload,
                                        self.server_playback_path
                                    )
                                else:
                                    self.prompt_onekey(
                                        "Stop current server replay?",
                                        (
                                            ("yes", "y"),
                                            ("no", "n"),
                                        ),
                                        self.stop_server_playback_prompt,
                                    )
                            elif k == "L":
                                self.path_prompt(
                                    "Load flows: ",
                                    self.state.last_saveload,
                                    self.load_flows_callback
                                )
                            elif k == "o":
                                self.prompt_onekey(
                                        "Options",
                                        (
                                            ("anticache", "a"),
                                            ("anticomp", "c"),
                                            ("killextra", "k"),
                                            ("norefresh", "n"),
                                        ),
                                        self._change_options
                                )
                            elif k == "t":
                                self.prompt(
                                    "Sticky cookie filter: ",
                                    self.stickycookie_txt,
                                    self.set_stickycookie
                                )
                            elif k == "u":
                                self.prompt(
                                    "Sticky auth filter: ",
                                    self.stickyauth_txt,
                                    self.set_stickyauth
                                )
                self.looptime = time.time() - startloop
        except (Stop, KeyboardInterrupt):
            pass

    def stop_client_playback_prompt(self, a):
        if a != "n":
            self.stop_client_playback()

    def stop_server_playback_prompt(self, a):
        if a != "n":
            self.stop_server_playback()

    def quit(self, a):
        if a != "n":
            raise Stop

    def _change_options(self, a):
        if a == "a":
            self.anticache = not self.anticache
        if a == "c":
            self.anticomp = not self.anticomp
        elif a == "k":
            self.killextra = not self.killextra
        elif a == "n":
            self.refresh_server_playback = not self.refresh_server_playback

    def shutdown(self):
        self.state.killall(self)
        controller.Master.shutdown(self)

    def sync_list_view(self):
        self.conn_list_view._modified()

    def clear_connections(self):
        self.state.clear()
        self.sync_list_view()

    def delete_connection(self, f):
        self.state.delete_flow(f)
        self.sync_list_view()

    def refresh_connection(self, c):
        if hasattr(self.header, "refresh_connection"):
            self.header.refresh_connection(c)
        if hasattr(self.body, "refresh_connection"):
            self.body.refresh_connection(c)
        if hasattr(self.statusbar, "refresh_connection"):
            self.statusbar.refresh_connection(c)

    def process_flow(self, f, r):
        if self.state.intercept and f.match(self.state.intercept) and not f.request.is_replay():
            f.intercept()
        else:
            r._ack()
        self.sync_list_view()
        self.refresh_connection(f)

    def clear_events(self):
        self.eventlist[:] = []

    def add_event(self, e, level="info"):
        if level == "info":
            e = urwid.Text(e)
        elif level == "error":
            e = urwid.Text(("error", e))

        self.eventlist.append(e)
        if len(self.eventlist) > EVENTLOG_SIZE:
            self.eventlist.pop(0)
        self.eventlist.set_focus(len(self.eventlist))

    # Handlers
    def handle_error(self, r):
        f = flow.FlowMaster.handle_error(self, r)
        if f:
            self.process_flow(f, r)
        return f

    def handle_request(self, r):
        f = flow.FlowMaster.handle_request(self, r)
        if f:
            self.process_flow(f, r)
        return f

    def handle_response(self, r):
        f = flow.FlowMaster.handle_response(self, r)
        if f:
            self.process_flow(f, r)
        return f

