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

import mailcap, mimetypes, tempfile, os, subprocess, glob, time, shlex, stat
import os.path, sys, weakref
import urwid
from .. import controller, utils, flow
import flowlist, flowview, help, common, grideditor, palettes, contentview, flowdetailview

EVENTLOG_SIZE = 500


class Stop(Exception): pass


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

#begin nocover

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
        self.expire = None

    def selectable(self):
        return True

    def path_prompt(self, prompt, text):
        self.expire = None
        self.w = PathEdit(prompt, text)

    def prompt(self, prompt, text = ""):
        self.expire = None
        # A (partial) workaround for this Urwid issue:
        # https://github.com/Nic0/tyrs/issues/115
        # We can remove it once veryone is beyond 1.0.1
        if isinstance(prompt, basestring):
            prompt = unicode(prompt)
        self.w = urwid.Edit(prompt, text or "")

    def message(self, message, expire=None):
        self.expire = expire
        self.w = urwid.Text(message)


class StatusBar(common.WWrap):
    def __init__(self, master, helptext):
        self.master, self.helptext = master, helptext
        self.ab = ActionBar()
        self.ib = common.WWrap(urwid.Text(""))
        self.w = urwid.Pile([self.ib, self.ab])

    def get_status(self):
        r = []

        if self.master.setheaders.count():
            r.append("[")
            r.append(("heading_key", "H"))
            r.append("eaders]")
        if self.master.replacehooks.count():
            r.append("[")
            r.append(("heading_key", "R"))
            r.append("eplacing]")
        if self.master.client_playback:
            r.append("[")
            r.append(("heading_key", "cplayback"))
            r.append(":%s to go]"%self.master.client_playback.count())
        if self.master.server_playback:
            r.append("[")
            r.append(("heading_key", "splayback"))
            if self.master.nopop:
                r.append(":%s in file]"%self.master.server_playback.count())
            else:
                r.append(":%s to go]"%self.master.server_playback.count())
        if self.master.state.intercept_txt:
            r.append("[")
            r.append(("heading_key", "i"))
            r.append(":%s]"%self.master.state.intercept_txt)
        if self.master.state.limit_txt:
            r.append("[")
            r.append(("heading_key", "l"))
            r.append(":%s]"%self.master.state.limit_txt)
        if self.master.stickycookie_txt:
            r.append("[")
            r.append(("heading_key", "t"))
            r.append(":%s]"%self.master.stickycookie_txt)
        if self.master.stickyauth_txt:
            r.append("[")
            r.append(("heading_key", "u"))
            r.append(":%s]"%self.master.stickyauth_txt)
        if self.master.server.config.reverse_proxy:
            r.append("[")
            r.append(("heading_key", "P"))
            r.append(":%s]"%utils.unparse_url(*self.master.server.config.reverse_proxy))
        if self.master.state.default_body_view.name != "Auto":
            r.append("[")
            r.append(("heading_key", "M"))
            r.append(":%s]"%self.master.state.default_body_view.name)

        opts = []
        if self.master.anticache:
            opts.append("anticache")
        if self.master.anticomp:
            opts.append("anticomp")
        if self.master.showhost:
            opts.append("showhost")
        if not self.master.refresh_server_playback:
            opts.append("norefresh")
        if self.master.killextra:
            opts.append("killextra")
        if self.master.server.config.no_upstream_cert:
            opts.append("no-upstream-cert")
        if self.master.state.follow_focus:
            opts.append("following")

        if opts:
            r.append("[%s]"%(":".join(opts)))

        if self.master.script:
            r.append("[script:%s]"%self.master.script.path)

        if self.master.debug:
            r.append("[lt:%0.3f]"%self.master.looptime)

        if self.master.stream:
            r.append("[W:%s]"%self.master.stream_path)

        return r

    def redraw(self):
        if self.ab.expire and time.time() > self.ab.expire:
            self.message("")

        fc = self.master.state.flow_count()
        if self.master.currentflow:
            idx = self.master.state.view.index(self.master.currentflow) + 1
            t = [
                ('heading', ("[%s/%s]"%(idx, fc)).ljust(9))
            ]
        else:
            t = [
                ('heading', ("[%s]"%fc).ljust(9))
            ]

        if self.master.server.bound:
            boundaddr = "[%s:%s]"%(self.master.server.address or "*", self.master.server.port)
        else:
            boundaddr = ""
        t.extend(self.get_status())
        status = urwid.AttrWrap(urwid.Columns([
            urwid.Text(t),
            urwid.Text(
                [
                    self.helptext,
                    boundaddr
                ],
                align="right"
            ),
        ]), "heading")
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
            expire = time.time() + float(expire)/1000
        self.ab.message(msg, expire)
        self.master.drawscreen()


#end nocover

class ConsoleState(flow.State):
    def __init__(self):
        flow.State.__init__(self)
        self.focus = None
        self.follow_focus = None
        self.default_body_view = contentview.get("Auto")
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

    def add_request(self, req):
        f = flow.State.add_request(self, req)
        if self.focus is None:
            self.set_focus(0)
        elif self.follow_focus:
            self.set_focus(len(self.view) - 1)
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
    attributes = [
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
        "showhost",
        "replacements",
        "rheaders",
        "setheaders",
        "server_replay",
        "stickycookie",
        "stickyauth",
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


#begin nocover


class ConsoleMaster(flow.FlowMaster):
    palette = []
    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, server, ConsoleState())
        self.looptime = 0
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

        self.refresh_server_playback = options.refresh_server_playback
        self.anticache = options.anticache
        self.anticomp = options.anticomp
        self.killextra = options.kill
        self.rheaders = options.rheaders
        self.nopop = options.nopop
        self.showhost = options.showhost

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

        if options.wfile:
            err = self.start_stream(options.wfile)
            if err:
                print >> sys.stderr, "Script load error:", err
                sys.exit(1)

    def start_stream(self, path):
        path = os.path.expanduser(path)
        try:
            f = file(path, "wb")
            flow.FlowMaster.start_stream(self, f, None)
        except IOError, v:
            return str(v)
        self.stream_path = path


    def _run_script_method(self, method, s, f):
        status, val = s.run(method, f)
        if val:
            if status:
                self.add_event("Method %s return: %s"%(method, val))
            else:
                self.add_event("Method %s error: %s"%(method, val[1]))

    def run_script_once(self, path, f):
        if not path:
            return
        self.add_event("Running script on flow: %s"%path)
        ret = self.get_script(path)
        if ret[0]:
            self.statusbar.message("Error loading script.")
            self.add_event("Error loading script:\n%s"%ret[0])
            return
        s = ret[1]
        if f.request:
            self._run_script_method("request", s, f)
        if f.response:
            self._run_script_method("response", s, f)
        if f.error:
            self._run_script_method("error", s, f)
        s.run("done")
        self.refresh_flow(f)
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
        self.view_flowlist()

    def _readflow(self, path):
        path = os.path.expanduser(path)
        try:
            f = file(path, "rb")
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
                False, self.nopop
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
            self.statusbar.message("Can't start editor: %s" % " ".join(c))
        else:
            data = open(name,"rb").read()
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
            self.statusbar.message("Can't start external viewer: %s" % " ".join(c))
        self.ui.start()
        os.unlink(name)

    def set_palette(self, name):
        self.palette = palettes.palettes[name]

    def run(self):
        self.currentflow = None

        self.ui = urwid.raw_display.Screen()
        self.ui.set_terminal_properties(256)
        self.ui.register_palette(self.palette)
        self.flow_list_walker = flowlist.FlowListWalker(self, self.state)

        self.view = None
        self.statusbar = None
        self.header = None
        self.body = None
        self.help_context = None

        self.prompting = False
        self.onekey = False

        self.view_flowlist()

        self.server.start_slave(controller.Slave, controller.Channel(self.masterq))

        if self.options.rfile:
            ret = self.load_flows(self.options.rfile)
            if ret and self.state.flow_count():
                self.add_event("File truncated or corrupted. Loaded as many flows as possible.")
            elif not self.state.flow_count():
                self.shutdown()
                print >> sys.stderr, "Could not load file:", ret
                sys.exit(1)

        self.ui.run_wrapper(self.loop)
        # If True, quit just pops out to flow list view.
        print >> sys.stderr, "Shutting down..."
        sys.stderr.flush()
        self.shutdown()

    def focus_current(self):
        if self.currentflow:
            try:
                self.flow_list_walker.set_focus(self.state.view.index(self.currentflow))
            except (IndexError, ValueError):
                pass

    def make_view(self):
        self.view = urwid.Frame(
                        self.body,
                        header = self.header,
                        footer = self.statusbar
                    )
        self.view.set_focus("body")

    def view_help(self):
        h = help.HelpView(self, self.help_context, (self.statusbar, self.body, self.header))
        self.statusbar = StatusBar(self, help.footer)
        self.body = h
        self.header = None
        self.make_view()

    def view_flowdetails(self, flow):
        h = flowdetailview.FlowDetailsView(self, flow, (self.statusbar, self.body, self.header))
        self.statusbar = StatusBar(self, flowdetailview.footer)
        self.body = h
        self.header = None
        self.make_view()

    def view_grideditor(self, ge):
        self.body = ge
        self.header = None
        self.help_context = ge.make_help()
        self.statusbar = StatusBar(self, grideditor.footer)
        self.make_view()

    def view_flowlist(self):
        if self.ui.started:
            self.ui.clear()
        if self.state.follow_focus:
            self.state.set_focus(self.state.flow_count())
        else:
            self.focus_current()

        if self.eventlog:
            self.body = flowlist.BodyPile(self)
        else:
            self.body = flowlist.FlowListBox(self)
        self.statusbar = StatusBar(self, flowlist.footer)
        self.header = None
        self.currentflow = None

        self.make_view()
        self.help_context = flowlist.help_context

    def view_flow(self, flow):
        self.body = flowview.FlowView(self, self.state, flow)
        self.header = flowview.FlowViewHeader(self, flow)
        self.statusbar = StatusBar(self, flowview.footer)
        self.currentflow = flow

        self.make_view()
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
            f = file(path, "rb")
            fr = flow.FlowReader(f)
        except IOError, v:
            return v.strerror
        reterr = None
        try:
            flow.FlowMaster.load_flows(self, fr)
        except flow.FlowReadError, v:
            reterr = v.strerror
        f.close()
        if self.flow_list_walker:
            self.sync_list_view()
            self.focus_current()
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
        v = self.state.set_limit(txt)
        self.sync_list_view()
        return v

    def set_intercept(self, txt):
        return self.state.set_intercept(txt)

    def change_default_display_mode(self, t):
        v = contentview.get_by_shortcut(t)
        self.state.default_body_view = v
        if self.currentflow:
            self.refresh_flow(self.currentflow)

    def set_reverse_proxy(self, txt):
        if not txt:
            self.server.config.reverse_proxy = None
        else:
            s = utils.parse_proxy_spec(txt)
            if not s:
                return "Invalid reverse proxy specification"
            self.server.config.reverse_proxy = s

    def drawscreen(self):
        size = self.ui.get_cols_rows()
        canvas = self.view.render(size, focus=1)
        self.ui.draw_screen(size, canvas)
        return size

    def pop_view(self):
        if self.currentflow:
            self.view_flow(self.currentflow)
        else:
            self.view_flowlist()

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
                            elif k == "H":
                                self.view_grideditor(
                                    grideditor.SetHeadersEditor(
                                        self,
                                        self.setheaders.get_specs(),
                                        self.setheaders.set
                                    )
                                )
                            elif k == "i":
                                self.prompt(
                                    "Intercept filter: ",
                                    self.state.intercept_txt,
                                    self.set_intercept
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
                            elif k == "M":
                                self.prompt_onekey(
                                    "Global default display mode",
                                    contentview.view_prompts,
                                    self.change_default_display_mode
                                )
                            elif k == "P":
                                if self.server.config.reverse_proxy:
                                    p = utils.unparse_url(*self.server.config.reverse_proxy)
                                else:
                                    p = ""
                                self.prompt(
                                    "Reverse proxy: ",
                                    p,
                                    self.set_reverse_proxy
                                )
                            elif k == "R":
                                self.view_grideditor(
                                    grideditor.ReplaceEditor(
                                        self,
                                        self.replacehooks.get_specs(),
                                        self.replacehooks.set
                                    )
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
                                        "Server replay path: ",
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
                            elif k == "o":
                                self.prompt_onekey(
                                        "Options",
                                        (
                                            ("anticache", "a"),
                                            ("anticomp", "c"),
                                            ("showhost", "h"),
                                            ("killextra", "k"),
                                            ("norefresh", "n"),
                                            ("no-upstream-certs", "u"),
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
        if a == "h":
            self.showhost = not self.showhost
            self.sync_list_view()
            self.refresh_flow(self.currentflow)
        elif a == "k":
            self.killextra = not self.killextra
        elif a == "n":
            self.refresh_server_playback = not self.refresh_server_playback
        elif a == "u":
            self.server.config.no_upstream_cert = not self.server.config.no_upstream_cert

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

    def refresh_flow(self, c):
        if hasattr(self.header, "refresh_flow"):
            self.header.refresh_flow(c)
        if hasattr(self.body, "refresh_flow"):
            self.body.refresh_flow(c)
        if hasattr(self.statusbar, "refresh_flow"):
            self.statusbar.refresh_flow(c)

    def process_flow(self, f, r):
        if self.state.intercept and f.match(self.state.intercept) and not f.request.is_replay():
            f.intercept()
        else:
            r.reply()
        self.sync_list_view()
        self.refresh_flow(f)

    def clear_events(self):
        self.eventlist[:] = []

    def add_event(self, e, level="info"):
        if level == "info":
            e = urwid.Text(str(e))
        elif level == "error":
            e = urwid.Text(("error", str(e)))

        self.eventlist.append(e)
        if len(self.eventlist) > EVENTLOG_SIZE:
            self.eventlist.pop(0)
        self.eventlist.set_focus(len(self.eventlist)-1)

    # Handlers
    def handle_log(self, l):
        self.add_event(l.msg)
        l.reply()

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
