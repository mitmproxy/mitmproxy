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

import Queue, mailcap, mimetypes, tempfile, os, subprocess, glob
import os.path, sys
import cStringIO
import urwid.curses_display
import urwid
import controller, utils, filt, proxy, flow


class Stop(Exception): pass


def format_keyvals(lst, key="key", val="text", space=5, indent=0):
    ret = []
    if lst:
        pad = max(len(i[0]) for i in lst) + space
        for i in lst:
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


#begin nocover

def int_version(v):
    SIG = 3
    v = urwid.__version__.split(".")
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
    def __init__(self, master, state, flow):
        self.master, self.state, self.flow = master, state, flow
        w = self.get_text()
        WWrap.__init__(self, w)

    def intercept(self):
        self.intercepting = True
        self.w = self.get_text()

    def get_text(self):
        return urwid.Text(self.flow.get_text())

    def selectable(self):
        return True

    def keypress(self, (maxcol,), key):
        if key == "a":
            self.flow.accept_intercept()
            self.master.sync_list_view()
        elif key == "A":
            self.master.accept_all()
            self.master.sync_list_view()
        elif key == "d":
            if not self.state.delete_flow(self.flow):
                self.master.statusbar.message("Can't delete connection mid-intercept.")
            self.master.sync_list_view()
        elif key == "r":
            r = self.state.replay(self.flow, self.master.masterq)
            if r:
                self.master.statusbar.message(r)
            self.master.sync_list_view()
        elif key == "R":
            self.state.revert(self.flow)
            self.master.sync_list_view()
        elif key == "s":
            self.master.prompt("Save this flow: ", self.master.save_one_flow, self.flow)
        elif key == "z":
            self.master.kill_connection(self.flow)
        elif key == "enter":
            if self.flow.request:
                self.master.view_connection(self.flow)
        return key


class ConnectionListView(urwid.ListWalker):
    def __init__(self, master, state):
        self.master, self.state = master, state
        if self.state.flow_list:
            self.set_focus(0)

    def get_focus(self):
        f, i = self.state.get_focus()
        f = ConnectionItem(self.master, self.state, f) if f else None
        return f, i

    def set_focus(self, focus):
        ret = self.state.set_focus(focus)
        self._modified()
        return ret

    def get_next(self, pos):
        f, i = self.state.get_next(pos)
        f = ConnectionItem(self.master, self.state, f) if f else None
        return f, i

    def get_prev(self, pos):
        f, i = self.state.get_prev(pos)
        f = ConnectionItem(self.master, self.state, f) if f else None
        return f, i


class ConnectionViewHeader(WWrap):
    def __init__(self, flow):
        self.flow = flow
        self.w = urwid.Text(flow.get_text(nofocus=True, padding=0))

    def refresh_connection(self, f):
        if f == self.flow:
            self.w = urwid.Text(f.get_text(nofocus=True, padding=0))

VIEW_NORMAL = 0
VIEW_BINARY = 1
VIEW_PRETTY = 2

class ConnectionView(WWrap):
    REQ = 0
    RESP = 1
    tabs = ["Request", "Response"]
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
        if active == self.REQ:
            parts.append(self._tab(qt, True))
        else:
            parts.append(self._tab(qt, False))

        if self.flow.response:
            if self.flow.intercepting and not self.flow.response.acked:
                st = "Response (intercepted)"
            else:
                st = "Response"
            if active == self.RESP:
                parts.append(self._tab(st, True))
            else:
                parts.append(self._tab(st, False))

        h = urwid.Columns(parts, dividechars=1)
        f = urwid.Frame(
                    body,
                    header=h
                )
        return f

    def _view_normal(self, conn, txt):
        for i in conn.content.splitlines():
            txt.append(
                ("text", i),
            )
            txt.append(
                ("text", "\n"),
            )

    def _view_binary(self, conn, txt):
        for offset, hex, s in utils.hexdump(conn.content):
            txt.extend([
                ("offset", offset),
                " ",
                ("text", hex),
                "   ",
                ("text", s),
                "\n"
            ])

    def _view_pretty(self, conn, txt):
        for i in utils.prettybody(conn.content):
            txt.append(
                ("text", i),
            )
            txt.append(
                ("text", "\n"),
            )

    def _conn_text(self, conn):
        txt = []
        txt.extend(
            format_keyvals(
                [(h+":", v) for (h, v) in sorted(conn.headers.itemPairs())],
                key = "header",
                val = "text"
            )
        )
        txt.append("\n\n")
        if conn.content:
            if utils.isBin(conn.content):
                self._view_binary(conn, txt)
            elif self.state.viewmode == VIEW_BINARY:
                self._view_binary(conn, txt)
            elif self.state.viewmode == VIEW_PRETTY:
                self._view_pretty(conn, txt)
            else:
                self._view_normal(conn, txt)
        return urwid.ListBox([urwid.Text(txt)])

    def view_request(self):
        self.viewing = self.REQ
        body = self._conn_text(self.flow.request)
        self.w = self.wrap_body(self.REQ, body)

    def view_response(self):
        if self.flow.response:
            self.viewing = self.RESP
            body = self._conn_text(self.flow.response)
            self.w = self.wrap_body(self.RESP, body)

    def refresh_connection(self, c=None):
        if c == self.flow:
            if self.viewing == self.REQ:
                self.view_request()
            else:
                self.view_response()

    def _spawn_editor(self, data):
        fd, name = tempfile.mkstemp('', "mproxy")
        os.write(fd, data)
        os.close(fd)
        c = os.environ.get("EDITOR")
        #If no EDITOR is set, assume 'vi'
        if not c:
            c = "vi"
        cmd = [c, name]
        try:
            ret = subprocess.call(cmd)
        except:
            self.master.statusbar.message("Can't start editor: %s" % c)
            self.master.ui._curs_set(1)
            self.master.ui.clear()
            os.unlink(name)
            return data
        # Not sure why, unless we do this we get a visible cursor after
        # spawning 'less'.
        self.master.ui._curs_set(1)
        self.master.ui.clear()
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
        if self.viewing == self.REQ:
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

    def edit(self, part):
        if self.viewing == self.REQ:
            conn = self.flow.request
        else:
            conn = self.flow.response
        if part == "b":
            conn.content = self._spawn_editor(conn.content or "")
        elif part == "h":
            headertext = self._spawn_editor(repr(conn.headers))
            headers = utils.Headers()
            fp = cStringIO.StringIO(headertext)
            headers.read(fp)
            conn.headers = headers
        elif part == "u" and self.viewing == self.REQ:
            conn = self.flow.request
            url = self._spawn_editor(conn.url())
            url = url.strip()
            if not conn.set_url(url):
                return "Invalid URL."
        elif part == "m" and self.viewing == self.REQ:
            self.master.prompt_onekey("Method ", self.methods, self.edit_method)
            key = None
        self.master.refresh_connection(self.flow)

    def keypress(self, size, key):
        if key == "tab":
            if self.viewing == self.REQ:
                self.view_response()
            else:
                self.view_request()
        elif key in ("up", "down", "page up", "page down"):
            # Why doesn't this just work??
            self.w.body.keypress(size, key)
        elif key == "a":
            self.flow.accept_intercept()
            self.master.view_connection(self.flow)
        elif key == "A":
            self.master.accept_all()
            self.master.view_connection(self.flow)
        elif key == "b":
            self.state.viewmode = VIEW_BINARY
            self.master.refresh_connection(self.flow)
        elif key == "n":
            self.state.viewmode = VIEW_NORMAL
            self.master.refresh_connection(self.flow)
        elif key == "p":
            self.state.viewmode = VIEW_PRETTY
            self.master.refresh_connection(self.flow)
        elif key == "e":
            if self.viewing == self.REQ:
                self.master.prompt_onekey(
                    "Edit request ",
                    (
                        ("header", "h"),
                        ("body", "b"),
                        ("url", "u"),
                        ("method", "m")
                    ),
                    self.edit
                )
            else:
                self.master.prompt_onekey(
                    "Edit response ",
                    (
                        ("header", "h"),
                        ("body", "b"),
                    ),
                    self.edit
                )
            key = None
        elif key == "r":
            r = self.state.replay(self.flow, self.master.masterq)
            if r:
                self.master.statusbar.message(r)
            self.master.refresh_connection(self.flow)
        elif key == "R":
            self.state.revert(self.flow)
            self.master.refresh_connection(self.flow)
        elif key == "s":
            self.master.prompt("Save this flow: ", self.master.save_one_flow, self.flow)
        elif key == "v":
            if self.viewing == self.REQ:
                conn = self.flow.request
            else:
                conn = self.flow.response
            if conn.content:
                t = conn.headers.get("content-type", [None])
                t = t[0]
                if t:
                    ext = mimetypes.guess_extension(t) or ""
                else:
                    ext = ""
                fd, name = tempfile.mkstemp(ext, "mproxy")
                os.write(fd, conn.content)
                os.close(fd)
                t = conn.headers.get("content-type", [None])
                t = t[0]

                cmd = None
                shell = False

                if t:
                    c = mailcap.getcaps()
                    cmd, _ = mailcap.findmatch(c, t, filename=name)
                    if cmd:
                        shell = True
                if not cmd:
                    c = os.environ.get("PAGER") or os.environ.get("EDITOR")
                    cmd = [c, name]
                ret = subprocess.call(cmd, shell=shell)
                # Not sure why, unless we do this we get a visible cursor after
                # spawning 'less'.
                self.master.ui._curs_set(1)
                self.master.ui.clear()
                os.unlink(name)
        elif key == "w":
            if self.viewing == self.REQ:
                self.master.prompt("Save request body: ", self.save_body)
            else:
                self.master.prompt("Save response body: ", self.save_body)
        return key


class _PathCompleter:
    DEFAULTPATH = "/bin:/usr/bin:/usr/local/bin"
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
                prefix = prefix.rstrip("/") or "./"
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

    def path_prompt(self, prompt):
        self.w = PathEdit(prompt)

    def prompt(self, prompt):
        self.w = urwid.Edit(prompt)

    def message(self, message):
        self.w = urwid.Text(message)


class StatusBar(WWrap):
    def __init__(self, master, text):
        self.master, self.text = master, text
        self.ab = ActionBar()
        self.ib = urwid.AttrWrap(urwid.Text(""), 'foot')
        self.w = urwid.Pile([self.ib, self.ab])
        self.redraw()

    def redraw(self):
        status = urwid.Columns([
            urwid.Text([('title', "mproxy:%s"%self.master.server.port)]),
            urwid.Text(
                [
                    self.text,
                    ('text', "%5s"%("[%s]"%len(self.master.state.flow_list)))
                ],
                align="right"),
        ])
        self.ib.set_w(status)

    def update(self, text):
        self.text = text
        self.redraw()

    def selectable(self):
        return True

    def get_edit_text(self):
        return self.ab.w.get_edit_text()

    def path_prompt(self, prompt):
        return self.ab.path_prompt(prompt)

    def prompt(self, prompt):
        return self.ab.prompt(prompt)

    def message(self, msg):
        self.ab.message(msg)


#end nocover

class ConsoleFlow(flow.Flow):
    def __init__(self, connection):
        flow.Flow.__init__(self, connection)
        self.focus = False

    def get_text(self, nofocus=False, padding=3):
        if not self.request and not self.response:
            txt = [
                ("title", " Connection from %s..."%(self.connection.address)),
            ]
        else:
            txt = [
                ("ack", "!") if self.intercepting and not self.request.acked else " ",
                ("method", self.request.method),
                " ",
                (
                    "text" if (self.response or self.error) else "title",
                    self.request.url(),
                ),
            ]
            if self.response or self.error or self.is_replay():
                txt.append("\n" + " "*(padding+2))
                if self.is_replay():
                    txt.append(("method", "[replay] "))
                if not (self.response or self.error):
                    txt.append(("text", "waiting for response..."))

            if self.response:
                txt.append(
                   ("ack", "!") if self.intercepting and not self.response.acked else " "
                )
                txt.append("-> ")
                if self.response.code in [200, 304]:
                    txt.append(("goodcode", str(self.response.code)))
                else:
                    txt.append(("error", str(self.response.code)))
                t = self.response.headers.get("content-type")
                if t:
                    t = t[0].split(";")[0]
                    txt.append(("text", " %s"%t))
                if self.response.content:
                    txt.append(", %s"%utils.pretty_size(len(self.response.content)))
            elif self.error:
                txt.append(
                   ("error", self.error.msg)
                )
        if self.focus and not nofocus:
            txt.insert(0, ("focus", ">>" + " "*(padding-2)))
        else:
            txt.insert(0, " "*padding)
        return txt


class ConsoleState(flow.State):
    def __init__(self):
        flow.State.__init__(self)
        self.focus = None
        self.beep = None
        self.viewmode = VIEW_NORMAL

    def add_browserconnect(self, f):
        flow.State.add_browserconnect(self, f)
        if self.focus is None:
            self.set_focus(0)
        else:
            self.set_focus(self.focus + 1)

    def add_request(self, req):
        if self.focus is None:
            self.set_focus(0)
        return flow.State.add_request(self, req)

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
            for i in self.view:
                i.focus = False
            if idx >= len(self.view):
                idx = len(self.view) - 1
            elif idx < 0:
                idx = 0
            self.view[idx].focus = True
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


#begin nocover

class ConsoleMaster(controller.Master):
    palette = []
    footer_text_default = [
        ('key', "?"), ":help ",
        ('key', "q"), ":exit ",
    ]
    footer_text_connview = [
        ('key', "tab"), ":toggle view ",
        ('key', "?"), ":help ",
        ('key', "q"), ":back ",
    ]
    def __init__(self, server, options):
        self.conn_list_view = None
        self.set_palette()
        controller.Master.__init__(self, server)
        self.state = ConsoleState()

        r = self.set_limit(options.limit)
        if r:
            print >> sys.stderr, "Limit error:", r
            sys.exit(1)

        r = self.set_intercept(options.intercept)
        if r:
            print >> sys.stderr, "Intercept error:", r
            sys.exit(1)

        r = self.set_beep(options.beep)
        if r:
            print >> sys.stderr, "Beep error:", r
            sys.exit(1)

        r = self.set_stickycookie(options.sticky)
        if r:
            print >> sys.stderr, "Sticky cookies error:", r
            sys.exit(1)

        self.stickycookie = None
        self.stickyhosts = {}

    def set_palette(self):
        self.palette = [
            ('body', 'black', 'dark cyan', 'standout'),
            ('foot', 'light gray', 'default'),
            ('title', 'white', 'default',),
            ('editline', 'white', 'default',),

            # Help
            ('key', 'light cyan', 'default', 'underline'),
            ('head', 'white', 'default'),
            ('text', 'light gray', 'default'),

            # List and Connections
            ('method', 'dark cyan', 'default'),
            ('focus', 'yellow', 'default'),
            ('goodcode', 'light green', 'default'),
            ('error', 'light red', 'default'),
            ('header', 'dark cyan', 'default'),
            ('heading', 'white', 'dark blue'),
            ('inactive', 'dark gray', 'default'),
            ('ack', 'light red', 'default'),

            # Hex view
            ('offset', 'dark cyan', 'default'),
        ]

    def run(self):
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette(self.palette)
        self.conn_list_view = ConnectionListView(self, self.state)

        self.view = None
        self.statusbar = None
        self.header = None
        self.body = None

        self.prompting = False
        self.onekey = False
        self.view_connlist()

        self.ui.run_wrapper(self.loop)
        # If True, quit just pops out to connection list view.
        print >> sys.stderr, "Shutting down..."
        sys.stderr.flush()
        self.shutdown()
        self.nested = False

    def make_view(self):
        self.view = urwid.Frame(
                        self.body,
                        header = self.header,
                        footer = self.statusbar
                    )
        self.view.set_focus("body")

    def view_connlist(self):
        self.body = urwid.ListBox(self.conn_list_view)
        self.statusbar = StatusBar(self, self.footer_text_default)
        self.header = None
        self.nested = False
        self.make_view()

    def view_connection(self, flow):
        self.statusbar = StatusBar(self, self.footer_text_connview)
        self.body = ConnectionView(self, self.state, flow)
        self.header = ConnectionViewHeader(flow)
        self.nested = True
        self.make_view()

    def _write_flows(self, path, data):
        if not path:
            return 
        path = os.path.expanduser(path)
        try:
            f = file(path, "wb")
            f.write(data)
            f.close()
        except IOError, v:
            self.statusbar.message(v.strerror)

    def save_one_flow(self, path, flow):
        data = flow.dump()
        return self._write_flows(path, data)

    def save_flows(self, path):
        data = self.state.dump_flows()
        return self._write_flows(path, data)

    def load_flows(self, path):
        if not path:
            return 
        path = os.path.expanduser(path)
        try:
            f = file(path, "r")
            data = f.read()
            f.close()
        except IOError, v:
            return v.strerror
        self.state.load_flows(data, ConsoleFlow)
        if self.conn_list_view:
            self.conn_list_view.set_focus(0)
            self.sync_list_view()

    def helptext(self):
        text = []
        text.extend([("head", "Global keys:\n")])
        keys = [
            ("A", "accept all intercepted connections"),
            ("a", "accept this intercepted connection"),
            ("B", "set beep filter pattern"),
            ("c", "set sticky cookie expression"),
            ("i", "set interception pattern"),
            ("j, k", "up, down"),
            ("l", "set limit filter pattern"),
            ("L", "load saved flows"),
            ("q", "quit / return to connection list"),
            ("r", "replay request"),
            ("R", "revert changes to request"),
            ("S", "save all flows matching current limit"),
            ("page up/down", "page up/down"),
            ("space", "page down"),
            ("enter", "view connection"),
        ]
        text.extend(format_keyvals(keys, key="key", val="text", indent=4))

        text.extend([("head", "\n\nConnection list keys:\n")])
        keys = [
            ("C", "clear connection list"),
            ("d", "delete connection from view"),
            ("s", "save this t flow"),
            ("z", "kill and delete connection, even if it's mid-intercept"),
        ]
        text.extend(format_keyvals(keys, key="key", val="text", indent=4))

        text.extend([("head", "\n\nConnection view keys:\n")])
        keys = [
            ("b", "view hexdump"),
            ("n", "view normal"),
            ("p", "view prettyprint"),
            ("", ""),
            ("e", "edit response/request"),
            ("s", "save this flow"),
            ("v", "view contents in external viewer"),
            ("w", "save request or response body"),
            ("tab", "toggle response/request view"),
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

    def view_help(self):
        self.body = self.helptext()
        self.header = None
        self.nested = True
        self.make_view()

    def path_prompt(self, prompt, callback, *args):
        self.statusbar.path_prompt(prompt)
        self.view.set_focus("footer")
        self.prompting = (callback, args)

    def prompt(self, prompt, callback, *args):
        self.statusbar.prompt(prompt)
        self.view.set_focus("footer")
        self.prompting = (callback, args)

    def prompt_onekey(self, prompt, keys, callback):
        """
            Keys are a set of (word, key) tuples. The appropriate key in the
            word is highlighted. 
        """
        prompt = [prompt, "("]
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
        self.prompt(prompt, callback)

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
            self.statusbar.message(msg)

    def prompt_cancel(self):
        self.prompt_done()

    def accept_all(self):
        self.state.accept_all()

    def set_limit(self, txt):
        if txt:
            f = filt.parse(txt)
            if not f:
                return "Invalid filter expression."
            self.state.set_limit(f)
        else:
            self.state.set_limit(None)

    def set_intercept(self, txt):
        if txt:
            self.state.intercept = filt.parse(txt)
            if not self.state.intercept:
                return "Invalid filter expression."
        else:
            self.state.intercept = None

    def set_beep(self, txt):
        if txt:
            self.state.beep = filt.parse(txt)
            if not self.state.beep:
                return "Invalid filter expression."
        else:
            self.state.beep = None

    def set_stickycookie(self, txt):
        if txt:
            self.stickycookie = filt.parse(txt)
            if not self.stickycookie:
                return "Invalid filter expression."
        else:
            self.stickyhosts = {}
            self.stickycookie = None

    def drawscreen(self):
        size = self.ui.get_cols_rows()
        canvas = self.view.render(size, focus=1)
        self.ui.draw_screen(size, canvas)
        return size

    def loop(self):
        q = Queue.Queue()
        self.masterq = q
        slave = controller.Slave(q, self.server)
        slave.start()
        try:
            while not self._shutdown:
                size = self.drawscreen()
                self.statusbar.redraw()
                self.tick(q)
                self.ui.set_input_timeouts(max_wait=0.1)
                keys = self.ui.get_input()
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
                        elif k == "l":
                            self.prompt("Limit: ", self.set_limit)
                            self.sync_list_view()
                            k = None
                        elif k == "i":
                            self.prompt("Intercept: ", self.set_intercept)
                            self.sync_list_view()
                            k = None
                        elif k == "B":
                            self.prompt("Beep: ", self.set_beep)
                            k = None
                        elif k == "C":
                            self.clear_connections()
                        elif k == "j":
                            k = "down"
                        elif k == "k":
                            k = "up"
                        elif k == " ":
                            k = "page down"
                        elif k in ('q','Q'):
                            if self.nested:
                                self.view_connlist()
                            else:
                                raise Stop
                        elif k == "S":
                            self.path_prompt("Save flows: ", self.save_flows)
                            k = None
                        elif k == "L":
                            self.path_prompt("Load flows: ", self.load_flows)
                            k = None
                        elif k == "c":
                            self.prompt("Sticky cookie: ", self.set_stickycookie)
                            k = None
                    if k:
                        self.view.keypress(size, k)
        except (Stop, KeyboardInterrupt):
            pass

    def shutdown(self):
        for i in self.state.flow_list:
            i.kill()
        controller.Master.shutdown(self)

    def sync_list_view(self):
        self.conn_list_view._modified()

    def clear_connections(self):
        self.state.clear()
        self.sync_list_view()

    def delete_connection(self, f):
        self.state.delete_flow(f)
        self.sync_list_view()

    def kill_connection(self, f):
        self.state.kill_flow(f)

    def refresh_connection(self, c):
        if hasattr(self.header, "refresh_connection"):
            self.header.refresh_connection(c)
        if hasattr(self.body, "refresh_connection"):
            self.body.refresh_connection(c)
        if hasattr(self.statusbar, "refresh_connection"):
            self.statusbar.refresh_connection(c)

    def process_flow(self, f, r):
        if f.match(self.state.beep):
            urwid.curses_display.curses.beep()
        if f.match(self.state.intercept) and not f.is_replay():
            f.intercept()
        else:
            r.ack()
        self.sync_list_view()
        self.refresh_connection(f)

    # Handlers
    def handle_browserconnection(self, r):
        f = ConsoleFlow(r)
        self.state.add_browserconnect(f)
        r.ack()
        self.sync_list_view()

    def handle_error(self, r):
        f = self.state.add_error(r)
        if not f:
            r.ack()
        else:
            self.sync_list_view()
            self.refresh_connection(f)

    def handle_request(self, r):
        f = self.state.add_request(r)
        if not f:
            r.ack()
        else:
            if f.match(self.stickycookie):
                hid = (f.request.host, f.request.port)
                if f.request.headers.has_key("cookie"):
                    self.stickyhosts[hid] = f.request.headers["cookie"]
                elif hid in self.stickyhosts:
                    f.request.headers["cookie"] = self.stickyhosts[hid]
            self.process_flow(f, r)

    def handle_response(self, r):
        f = self.state.add_response(r)
        if not f:
            r.ack()
        else:
            if f.match(self.stickycookie):
                hid = (f.request.host, f.request.port)
                if f.response.headers.has_key("set-cookie"):
                    self.stickyhosts[hid] = f.response.headers["set-cookie"]
            self.process_flow(f, r)

