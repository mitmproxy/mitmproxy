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

import mailcap, mimetypes, tempfile, os, subprocess, glob, time
import os.path, sys
import cStringIO
import urwid.raw_display
import urwid
import controller, utils, filt, proxy, flow, encoding

VIEW_CUTOFF = 1024*100


class Stop(Exception): pass


def format_keyvals(lst, key="key", val="text", space=5, indent=0):
    ret = []
    if lst:
        pad = max(len(i[0]) for i in lst if i and i[0]) + space
        for i in lst:
            if i is None:
                ret.extend("\n")
            elif i[0] is None:
                ret.extend(
                    [
                        " "*(pad + indent),
                        (val, i[1]),
                        "\n"
                    ]
                )
            else:
                ret.extend(
                    [
                        " "*indent,
                        (key, i[0]),
                        " "*(pad-len(i[0])),
                        (val, i[1]),
                        "\n"
                    ]
                )
    return ret


def format_flow(f, focus, extended=False, padding=2):
    txt = []
    if extended:
        txt.append(("highlight", utils.format_timestamp(f.request.timestamp)))
    txt.append(" ")
    if f.request.is_replay():
        txt.append(("method", "[replay]"))
    txt.extend([
        ("ack", "!") if f.intercepting and not f.request.acked else " ",
        ("method", f.request.method),
        " ",
        (
            "text" if (f.response or f.error) else "title",
            f.request.url(),
        ),
    ])
    if f.response or f.error or f.request.is_replay():
        tsr = f.response or f.error
        if extended and tsr:
            ts = ("highlight", utils.format_timestamp(tsr.timestamp) + " ")
        else:
            ts = " "

        txt.append("\n")
        txt.append(("text", ts))
        txt.append(" "*(padding+2))
        met = ""

    if f.response:
        txt.append(
           ("ack", "!") if f.intercepting and not f.response.acked else " "
        )
        txt.append("<- ")
        if f.response.is_replay():
            txt.append(("method", "[replay] "))
        if f.response.code in [200, 304]:
            txt.append(("goodcode", str(f.response.code)))
        else:
            txt.append(("error", str(f.response.code)))
        t = f.response.headers["content-type"]
        if t:
            t = t[0].split(";")[0]
            txt.append(("text", " %s"%t))
        e = f.response.headers["content-encoding"]
        if e:
            e = e[0]
        else:
            e = "identity"
        if f.response.content:
            txt.append(", %s"%utils.pretty_size(len(f.response.content)))
    elif f.error:
        txt.append(
           ("error", f.error.msg)
        )

    if focus:
        txt.insert(0, ("focus", ">>" + " "*(padding-2)))
    else:
        txt.insert(0, " "*padding)
    return txt



#begin nocover

def int_version(v):
    SIG = 3
    v = urwid.__version__.split("-")[0].split(".")
    x = 0
    for i in range(min(SIG, len(v))):
        x += int(v[i]) * 10**(SIG-i)
    return x


# We have to do this to be portable over 0.9.8 and 0.9.9 If compatibility
# becomes a pain to maintain, we'll just mandate 0.9.9 or newer.
class WWrap(urwid.WidgetWrap):
    if int_version(urwid.__version__) >= 990:
        def set_w(self, x):
            self._w = x
        def get_w(self):
            return self._w
        w = property(get_w, set_w)


class ConnectionItem(WWrap):
    def __init__(self, master, state, flow, focus):
        self.master, self.state, self.flow = master, state, flow
        self.focus = focus
        w = self.get_text()
        WWrap.__init__(self, w)

    def get_text(self):
        return urwid.Text(format_flow(self.flow, self.focus))

    def selectable(self):
        return True

    def keypress(self, (maxcol,), key):
        if key == "a":
            self.flow.accept_intercept()
            self.master.sync_list_view()
        elif key == "A":
            self.master.accept_all()
            self.master.sync_list_view()
        elif key == "C":
            self.master.clear_connections()
        elif key == "d":
            self.flow.kill(self.master)
            self.state.delete_flow(self.flow)
            self.master.sync_list_view()
        elif key == "r":
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.sync_list_view()
        elif key == "R":
            self.state.revert(self.flow)
            self.master.sync_list_view()
        elif key == "w":
            self.master.path_prompt(
                "Save this flow: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )
        elif key == "z":
            self.flow.kill(self.master)
        elif key == "enter":
            if self.flow.request:
                self.master.view_flow(self.flow)
        elif key == " ":
            key = "page down"
        return key


class ConnectionListView(urwid.ListWalker):
    def __init__(self, master, state):
        self.master, self.state = master, state
        if self.state.flow_list:
            self.set_focus(0)

    def get_focus(self):
        f, i = self.state.get_focus()
        f = ConnectionItem(self.master, self.state, f, True) if f else None
        return f, i

    def set_focus(self, focus):
        ret = self.state.set_focus(focus)
        self._modified()
        return ret

    def get_next(self, pos):
        f, i = self.state.get_next(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i

    def get_prev(self, pos):
        f, i = self.state.get_prev(pos)
        f = ConnectionItem(self.master, self.state, f, False) if f else None
        return f, i


class ConnectionViewHeader(WWrap):
    def __init__(self, master, f):
        self.master, self.flow = master, f
        self.w = urwid.Text(format_flow(f, False, extended=True, padding=0))

    def refresh_connection(self, f):
        if f == self.flow:
            self.w = urwid.Text(format_flow(f, False, extended=True, padding=0))


VIEW_BODY_RAW = 0
VIEW_BODY_HEX = 1
VIEW_BODY_PRETTY = 2

BODY_VIEWS = {
    VIEW_BODY_RAW: "raw",
    VIEW_BODY_HEX: "hex",
    VIEW_BODY_PRETTY: "pretty"
}

VIEW_FLOW_REQUEST = 0
VIEW_FLOW_RESPONSE = 1

class ConnectionView(WWrap):
    REQ = 0
    RESP = 1
    methods = [
        ("get", "g"),
        ("post", "p"),
        ("put", "u"),
        ("head", "h"),
        ("trace", "t"),
        ("delete", "d"),
        ("options", "o"),
    ]
    def __init__(self, master, state, flow):
        self.master, self.state, self.flow = master, state, flow
        if self.state.view_flow_mode == VIEW_FLOW_RESPONSE and flow.response:
            self.view_response()
        else:
            self.view_request()

    def _tab(self, content, active):
        if active:
            attr = "heading"
        else:
            attr = "inactive"
        p = urwid.Text(content)
        p = urwid.Padding(p, align="left", width=("relative", 100))
        p = urwid.AttrWrap(p, attr)
        return p

    def wrap_body(self, active, body):
        parts = []

        if self.flow.intercepting and not self.flow.request.acked:
            qt = "Request (intercepted)"
        else:
            qt = "Request"
        if active == VIEW_FLOW_REQUEST:
            parts.append(self._tab(qt, True))
        else:
            parts.append(self._tab(qt, False))

        if self.flow.response:
            if self.flow.intercepting and not self.flow.response.acked:
                st = "Response (intercepted)"
            else:
                st = "Response"
            if active == VIEW_FLOW_RESPONSE:
                parts.append(self._tab(st, True))
            else:
                parts.append(self._tab(st, False))

        h = urwid.Columns(parts, dividechars=1)
        f = urwid.Frame(
                    body,
                    header=h
                )
        return f

    def _conn_text(self, conn, viewmode):
        if conn:
            e = conn.headers["content-encoding"]
            if e:
                e = e[0]
            else:
                e = "identity"
            return self.master._cached_conn_text(
                        encoding.decode(e, conn.content),
                        tuple([tuple(i) for i in conn.headers.lst]),
                        viewmode
                    )
        else:
            return urwid.ListBox([])

    def view_request(self):
        self.state.view_flow_mode = VIEW_FLOW_REQUEST
        self.master.statusbar.update("Calculating view...")
        body = self._conn_text(
            self.flow.request,
            self.state.view_body_mode
        )
        self.w = self.wrap_body(VIEW_FLOW_REQUEST, body)
        self.master.statusbar.update("")

    def view_response(self):
        self.state.view_flow_mode = VIEW_FLOW_RESPONSE
        self.master.statusbar.update("Calculating view...")
        body = self._conn_text(
            self.flow.response,
            self.state.view_body_mode
        )
        self.w = self.wrap_body(VIEW_FLOW_RESPONSE, body)
        self.master.statusbar.update("")

    def refresh_connection(self, c=None):
        if c == self.flow:
            if self.state.view_flow_mode == VIEW_FLOW_RESPONSE and self.flow.response:
                self.view_response()
            else:
                self.view_request()

    def _spawn_editor(self, data):
        fd, name = tempfile.mkstemp('', "mproxy")
        os.write(fd, data)
        os.close(fd)
        c = os.environ.get("EDITOR")
        #If no EDITOR is set, assume 'vi'
        if not c:
            c = "vi"
        cmd = [c, name]
        self.master.ui.stop()
        try:
            ret = subprocess.call(cmd)
        except:
            self.master.statusbar.message("Can't start editor: %s" % c)
            self.master.ui.start()
            os.unlink(name)
            return data
        self.master.ui.start()
        data = open(name).read()
        os.unlink(name)
        return data

    def edit_method(self, m):
        for i in self.methods:
            if i[1] == m:
                self.flow.request.method = i[0].upper()
        self.master.refresh_connection(self.flow)

    def save_body(self, path):
        if not path:
            return
        self.state.last_saveload = path
        if self.state.view_flow_mode == VIEW_FLOW_REQUEST:
            c = self.flow.request
        else:
            c = self.flow.response
        path = os.path.expanduser(path)
        try:
            f = file(path, "wb")
            f.write(str(c.content))
            f.close()
        except IOError, v:
            self.master.statusbar.message(v.strerror)

    def set_url(self, url):
        request = self.flow.request
        if not request.set_url(url):
            return "Invalid URL."
        self.master.refresh_connection(self.flow)

    def set_resp_code(self, code):
        response = self.flow.response
        try:
            response.code = int(code)
        except ValueError:
            return None
        import BaseHTTPServer
        if BaseHTTPServer.BaseHTTPRequestHandler.responses.has_key(int(code)):
            response.msg = BaseHTTPServer.BaseHTTPRequestHandler.responses[int(code)][0]
        self.master.refresh_connection(self.flow)

    def set_resp_msg(self, msg):
        response = self.flow.response
        response.msg = msg
        self.master.refresh_connection(self.flow)

    def edit(self, part):
        if self.state.view_flow_mode == VIEW_FLOW_REQUEST:
            conn = self.flow.request
        else:
            conn = self.flow.response

        self.flow.backup()
        if part == "b":
            conn.content = self._spawn_editor(conn.content or "")
        elif part == "h":
            headertext = self._spawn_editor(repr(conn.headers))
            headers = utils.Headers()
            fp = cStringIO.StringIO(headertext)
            headers.read(fp)
            conn.headers = headers
        elif part == "u" and self.state.view_flow_mode == VIEW_FLOW_REQUEST:
            self.master.prompt_edit("URL", conn.url(), self.set_url)
        elif part == "m" and self.state.view_flow_mode == VIEW_FLOW_REQUEST:
            self.master.prompt_onekey("Method", self.methods, self.edit_method)
        elif part == "c" and self.state.view_flow_mode == VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Code", str(conn.code), self.set_resp_code)
        elif part == "m" and self.state.view_flow_mode == VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Message", conn.msg, self.set_resp_msg)
        elif part == "r" and self.state.view_flow_mode == VIEW_FLOW_REQUEST:
            if not conn.acked:
                response = proxy.Response(conn, "200", "OK", utils.Headers(), "")
                conn.ack(response)
            self.view_response()
        self.master.refresh_connection(self.flow)

    def keypress(self, size, key):
        if key == "tab":
            if self.state.view_flow_mode == VIEW_FLOW_REQUEST and self.flow.response:
                self.view_response()
            else:
                self.view_request()
        elif key in ("up", "down", "page up", "page down"):
            # Why doesn't this just work??
            self.w.body.keypress(size, key)
        elif key == "a":
            self.flow.accept_intercept()
            self.master.view_flow(self.flow)
        elif key == "A":
            self.master.accept_all()
            self.master.view_flow(self.flow)
        elif key == "e":
            if self.state.view_flow_mode == VIEW_FLOW_REQUEST:
                self.master.prompt_onekey(
                    "Edit request",
                    (
                        ("header", "h"),
                        ("body", "b"),
                        ("url", "u"),
                        ("method", "m"),
                        ("reply", "r")
                    ),
                    self.edit
                )
            else:
                self.master.prompt_onekey(
                    "Edit response",
                    (
                        ("code", "c"),
                        ("message", "m"),
                        ("header", "h"),
                        ("body", "b"),
                    ),
                    self.edit
                )
            key = None
        elif key == "p":
            self.master.view_prev_flow(self.flow)
        elif key == "r":
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.refresh_connection(self.flow)
        elif key == "R":
            self.state.revert(self.flow)
            self.master.refresh_connection(self.flow)
        elif key == "w":
            self.master.path_prompt(
                "Save this flow: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )
        elif key == "v":
            if self.state.view_flow_mode == VIEW_FLOW_REQUEST:
                conn = self.flow.request
            else:
                conn = self.flow.response
            if conn.content:
                t = conn.headers["content-type"] or [None]
                t = t[0]
                self.master.spawn_external_viewer(conn.content, t)
        elif key == "b":
            if self.state.view_flow_mode == VIEW_FLOW_REQUEST:
                self.master.path_prompt(
                    "Save request body: ",
                    self.state.last_saveload,
                    self.save_body
                )
            else:
                self.master.path_prompt(
                    "Save response body: ",
                    self.state.last_saveload,
                    self.save_body
                )
        elif key == " ":
            self.master.view_next_flow(self.flow)
        elif key == "|":
            self.master.path_prompt("Script: ", self.state.last_script, self.run_script)
        return key

    def run_script(self, path):
        if path:
            self.master._runscript(self.flow, path)


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


class ActionBar(WWrap):
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


class StatusBar(WWrap):
    def __init__(self, master, helptext):
        self.master, self.helptext = master, helptext
        self.expire = None
        self.ab = ActionBar()
        self.ib = WWrap(urwid.Text(""))
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
        if not self.master.refresh_server_playback:
            opts.append("norefresh")
        if self.master.killextra:
            opts.append("killextra")

        if opts:
            r.append("[%s]"%(":".join(opts)))

        if self.master.debug:
            r.append("[lt:%0.3f]"%self.master.looptime)

        return r

    def redraw(self):
        if self.expire and time.time() > self.expire:
            self.message("")

        t = [
                ('statusbar_text', ("[%s]"%len(self.master.state.flow_list)).ljust(7)),
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
                    ('statusbar_text', (":%s]"%BODY_VIEWS[self.master.state.view_body_mode])),
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

        self.view_body_mode = VIEW_BODY_PRETTY
        self.view_flow_mode = VIEW_FLOW_REQUEST

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
        "keepserving",
        "kill",
        "intercept",
        "limit",
        "no_server",
        "refresh_server_playback",
        "request_script",
        "response_script",
        "rfile",
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
VIEW_CONNLIST = 0
VIEW_FLOW = 1
VIEW_HELP = 2

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

        if options.response_script:
            self.set_response_script(options.response_script)
        if options.request_script:
            self.set_request_script(options.request_script)

        r = self.set_limit(options.limit)
        if r:
            print >> sys.stderr, "Limit error:", r
            sys.exit(1)

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

        if options.client_replay:
            self.client_playback_path(options.client_replay)

        if options.server_replay:
            self.server_playback_path(options.server_replay)

        self.debug = options.debug


    def _runscript(self, f, path):
        path = os.path.expanduser(path)
        self.state.last_script = path
        try:
            serr = f.run_script(path)
        except flow.RunException, e:
            if e.errout:
                serr = "Script error code: %s\n\n"%e.returncode + e.errout
                self.spawn_external_viewer(serr, None)
            self.statusbar.message("Script error: %s"%e)
            return
        if serr:
            serr = "Script output:\n\n" + serr
            self.spawn_external_viewer(serr, None)
        self.refresh_connection(f)

    def _trailer(self, clen, txt):
        rem = clen - VIEW_CUTOFF
        if rem > 0:
            txt.append(urwid.Text(""))
            txt.append(
                urwid.Text(
                    [
                        ("highlight", "... %s of data not shown"%utils.pretty_size(rem))
                    ]
                )
            )

    def _view_conn_raw(self, content, txt):
        for i in utils.cleanBin(content[:VIEW_CUTOFF]).splitlines():
            txt.append(
                urwid.Text(("text", i))
            )
        self._trailer(len(content), txt)

    def _view_conn_binary(self, content, txt):
        for offset, hex, s in utils.hexdump(content[:VIEW_CUTOFF]):
            txt.append(urwid.Text([
                ("offset", offset),
                " ",
                ("text", hex),
                "   ",
                ("text", s),
            ]))
        self._trailer(len(content), txt)

    def _view_conn_xmlish(self, content, txt):
        for i in utils.pretty_xmlish(content[:VIEW_CUTOFF]):
            txt.append(
                urwid.Text(("text", i)),
            )
        self._trailer(len(content), txt)

    def _view_conn_json(self, lines, txt):
        sofar = 0
        for i in lines:
            sofar += len(i)
            txt.append(
                urwid.Text(("text", i)),
            )
            if sofar > VIEW_CUTOFF:
                break
        self._trailer(sum(len(i) for i in lines), txt)

    def _view_conn_urlencoded(self, lines, txt):
        txt.append(urwid.Text(("highlight", "URLencoded data:\n")))
        txt.append(
            urwid.Text(
                format_keyvals(
                    [(k+":", v) for (k, v) in lines],
                    key = "header",
                    val = "text"
                )
            )
        )

    def _find_pretty_view(self, content, hdrItems, txt):
        ctype = None
        for i in hdrItems:
            if i[0] == "content-type":
                ctype = i[1]
                break
        if ctype and "x-www-form-urlencoded" in ctype:
            data = utils.urldecode(content)
            if data:
                return self._view_conn_urlencoded(data, txt)
        if utils.isXML(content):
            return self._view_conn_xmlish(content, txt)
        elif ctype and "application/json" in ctype:
            lines = utils.pretty_json(content)
            if lines:
                return self._view_conn_json(lines, txt)
        return self._view_conn_raw(content, txt)

    @utils.LRUCache(20)
    def _cached_conn_text(self, content, hdrItems, viewmode):
        hdr = []
        hdr.extend(
            format_keyvals(
                [(h+":", v) for (h, v) in hdrItems],
                key = "header",
                val = "text"
            )
        )
        hdr.append("\n")

        txt = [urwid.Text(hdr)]
        if content:
            if viewmode == VIEW_BODY_HEX:
                self._view_conn_binary(content, txt)
            elif viewmode == VIEW_BODY_PRETTY:
                self._find_pretty_view(content, hdrItems, txt)
            else:
                self._view_conn_raw(content, txt)
        return urwid.ListBox(txt)

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
        ret = subprocess.call(cmd, shell=shell)
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
            ('highlight', 'white,bold', 'default'),
            ('inactive', 'dark gray', 'default'),
            ('ack', 'light red', 'default'),

            # Hex view
            ('offset', 'dark cyan', 'default'),
        ]

    def run(self):
        self.viewstate = VIEW_CONNLIST
        self.currentflow = None

        self.ui = urwid.raw_display.Screen()
        self.ui.register_palette(self.palette)
        self.conn_list_view = ConnectionListView(self, self.state)

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
            self.load_flows(self.options.rfile)

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
        self.body = self.helptext()
        self.header = None
        self.viewstate = VIEW_HELP
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
        self.body = urwid.ListBox(self.conn_list_view)
        self.statusbar = StatusBar(self, self.footer_text_default)
        self.header = None
        self.viewstate = VIEW_CONNLIST
        self.currentflow = None
        self.make_view()

    def view_flow(self, flow):
        self.statusbar = StatusBar(self, self.footer_text_connview)
        self.body = ConnectionView(self, self.state, flow)
        self.header = ConnectionViewHeader(self, flow)
        self.viewstate = VIEW_FLOW
        self.currentflow = flow
        self.make_view()

    def _view_nextprev_flow(self, np, flow):
        try:
            idx = self.state.view.index(flow)
        except IndexError:
            return
        if np == "next":
            new_flow, new_idx = self.state.get_next(idx)
        else:
            new_flow, new_idx = self.state.get_prev(idx)
        if new_idx is None:
            return
        self.view_flow(new_flow)

    def view_next_flow(self, flow):
        return self._view_nextprev_flow("next", flow)

    def view_prev_flow(self, flow):
        return self._view_nextprev_flow("prev", flow)

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

    def load_flows(self, path):
        if not path:
            return
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
        return "Flows loaded from %s"%path

    def helptext(self):
        text = []
        text.extend([("head", "Global keys:\n")])
        keys = [
            ("A", "accept all intercepted connections"),
            ("a", "accept this intercepted connection"),
            ("c", "client replay"),
            ("i", "set interception pattern"),
            ("j, k", "up, down"),
            ("l", "set limit filter pattern"),
            ("L", "load saved flows"),
            ("o", "toggle options:"),
            (None, "  anticache: modify requests to prevent cached responses"),
            (None, "  killextra: kill requests not part of server replay"),
            (None, "  norefresh: disable server replay response refresh"),
            ("q", "quit / return to connection list"),
            ("Q", "quit without confirm prompt"),
            ("r", "replay request"),
            ("R", "revert changes to request"),
            ("S", "save all flows matching current limit"),
            ("s", "server replay"),
            ("t", "set sticky cookie expression"),
            ("u", "set sticky auth expression"),
            ("w", "save this flow"),
            ("page up/down", "page up/down"),
            ("enter", "view connection"),
        ]
        text.extend(format_keyvals(keys, key="key", val="text", indent=4))

        text.extend([("head", "\n\nConnection list keys:\n")])
        keys = [
            ("C", "clear connection list"),
            ("d", "delete connection from view"),
            ("z", "kill and delete connection, even if it's mid-intercept"),
            ("space", "page down"),
        ]
        text.extend(format_keyvals(keys, key="key", val="text", indent=4))

        text.extend([("head", "\n\nConnection view keys:\n")])
        keys = [
            ("b", "save request/response body"),
            ("e", "edit request/response"),
            ("m", "change view mode (raw, pretty, hex)"),
            (None, "  raw: raw data"),
            (None, "  pretty: pretty-print XML, HTML and JSON"),
            (None, "  hex: hex dump"),
            ("p", "previous flow"),
            ("v", "view body in external viewer"),
            ("|", "run script"),
            ("tab", "toggle response/request view"),
            ("space", "next flow"),
        ]
        text.extend(format_keyvals(keys, key="key", val="text", indent=4))

        text.extend([("head", "\n\nFilter expressions:\n")])
        f = []
        for i in filt.filt_unary:
            f.append(
                ("~%s"%i.code, i.help)
            )
        for i in filt.filt_rex:
            f.append(
                ("~%s regex"%i.code, i.help)
            )
        for i in filt.filt_int:
            f.append(
                ("~%s int"%i.code, i.help)
            )
        f.sort()
        f.extend(
            [
                ("!", "unary not"),
                ("&", "and"),
                ("|", "or"),
                ("(...)", "grouping"),
            ]
        )
        text.extend(format_keyvals(f, key="key", val="text", indent=4))

        text.extend(
           [
                "\n",
                ("text", "    Regexes are Python-style.\n"),
                ("text", "    Regexes can be specified as quoted strings.\n"),
                ("text", "    Header matching (~h, ~hq, ~hs) is against a string of the form \"name: value\".\n"),
                ("text", "    Expressions with no operators are regex matches against URL.\n"),
                ("text", "    Default binary operator is &.\n"),
                ("head", "\n    Examples:\n"),
           ]
        )
        examples = [
                ("google\.com", "Url containing \"google.com"),
                ("~r ~b test", "Requests where body contains \"test\""),
                ("!(~r & ~t \"text/html\")", "Anything but requests with a text/html content type."),
        ]
        text.extend(format_keyvals(examples, key="key", val="text", indent=4))
        return urwid.ListBox([urwid.Text(text)])

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

    def prompt_onekey(self, prompt, keys, callback):
        """
            Keys are a set of (word, key) tuples. The appropriate key in the
            word is highlighted.
        """
        prompt = [prompt, " ("]
        mkup = []
        for i, e in enumerate(keys):
            parts = e[0].split(e[1], 1)
            if parts[0]:
                mkup.append(("text", parts[0]))
            mkup.append(("key", e[1]))
            if parts[1]:
                mkup.append(("text", parts[1]))
            if i < len(keys)-1:
                mkup.append(",")
        prompt.extend(mkup)
        prompt.append(")? ")
        self.onekey = "".join([i[1] for i in keys])
        self.prompt(prompt, "", callback)

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
            self.state.view_body_mode = VIEW_BODY_RAW
        elif v == "h":
            self.state.view_body_mode = VIEW_BODY_HEX
        elif v == "p":
            self.state.view_body_mode = VIEW_BODY_PRETTY
        self.refresh_connection(self.currentflow)

    def drawscreen(self):
        size = self.ui.get_cols_rows()
        canvas = self.view.render(size, focus=1)
        self.ui.draw_screen(size, canvas)
        return size

    def loop(self):
        changed = True
        try:
            while not controller.exit:
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
                            k = None
                        elif self.onekey:
                            if k == "enter":
                                self.prompt_cancel()
                            elif k in self.onekey:
                                self.prompt_execute(k)
                            k = None
                        elif k == "enter":
                            self.prompt_execute()
                            k = None
                    else:
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

                            k = None
                        elif k == "l":
                            self.prompt("Limit: ", self.state.limit_txt, self.set_limit)
                            self.sync_list_view()
                            k = None
                        elif k == "i":
                            self.prompt(
                                "Intercept filter: ",
                                self.state.intercept_txt,
                                self.set_intercept
                            )
                            self.sync_list_view()
                            k = None
                        elif k == "j":
                            k = "down"
                        elif k == "k":
                            k = "up"
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
                            k = None
                        elif k in ("q", "Q"):
                            if k == "Q":
                                raise Stop
                            if self.viewstate == VIEW_FLOW:
                                self.view_connlist()
                            elif self.viewstate == VIEW_HELP:
                                if self.currentflow:
                                    self.view_flow(self.currentflow)
                                else:
                                    self.view_connlist()
                            else:
                                self.prompt_onekey(
                                    "Quit",
                                    (
                                        ("yes", "y"),
                                        ("no", "n"),
                                    ),
                                    self.quit,
                                )
                            k = None
                        elif k == "S":
                            self.path_prompt(
                                "Save flows: ",
                                self.state.last_saveload,
                                self.save_flows
                            )
                            k = None
                        elif k == "s":
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
                            k = None
                        elif k == "L":
                            self.path_prompt(
                                "Load flows: ",
                                self.state.last_saveload,
                                self.load_flows
                            )
                            k = None
                        elif k == "o":
                            self.prompt_onekey(
                                    "Options",
                                    (
                                        ("anticache", "a"),
                                        ("killextra", "k"),
                                        ("norefresh", "n"),
                                    ),
                                    self._change_options
                            )
                            k = None
                        elif k == "t":
                            self.prompt(
                                "Sticky cookie filter: ",
                                self.stickycookie_txt,
                                self.set_stickycookie
                            )
                            k = None
                        elif k == "u":
                            self.prompt(
                                "Sticky auth filter: ",
                                self.stickyauth_txt,
                                self.set_stickyauth
                            )
                            k = None
                    if k:
                        self.view.keypress(size, k)
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
        elif a == "k":
            self.killextra = not self.killextra
        elif a == "n":
            self.refresh_server_playback = not self.refresh_server_playback

    def shutdown(self):
        for i in self.state.flow_list:
            i.kill(self)
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
        if f.match(self.state.intercept) and not f.request.is_replay():
            f.intercept()
        else:
            r.ack()
        self.sync_list_view()
        self.refresh_connection(f)

    # Handlers
    def handle_clientconnect(self, r):
        f = flow.FlowMaster.handle_clientconnect(self, r)
        if f:
            self.sync_list_view()

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

