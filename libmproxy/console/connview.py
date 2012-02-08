import urwid
import common
from .. import utils, encoding, flow

def _mkhelp():
    text = []
    keys = [
        ("A", "accept all intercepted connections"),
        ("a", "accept this intercepted connection"),
        ("b", "save request/response body"),
        ("e", "edit request/response"),
        ("m", "change body display mode"),
            (None,
                common.highlight_key("raw", "r") +
                [("text", ": raw data")]
            ),
            (None,
                common.highlight_key("pretty", "p") +
                [("text", ": pretty-print XML, HTML and JSON")]
            ),
            (None,
                common.highlight_key("hex", "h") +
                [("text", ": hex dump")]
            ),
        ("p", "previous flow"),
        ("v", "view body in external viewer"),
        ("z", "encode/decode a request/response"),
        ("tab", "toggle request/response view"),
        ("space", "next flow"),
        ("|", "run script on this flow"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()


VIEW_CUTOFF = 1024*100

class ConnectionViewHeader(common.WWrap):
    def __init__(self, master, f):
        self.master, self.flow = master, f
        self.w = urwid.Text(common.format_flow(f, False, extended=True, padding=0))

    def refresh_connection(self, f):
        if f == self.flow:
            self.w = urwid.Text(common.format_flow(f, False, extended=True, padding=0))


class CallbackCache:
    @utils.LRUCache(20)
    def callback(self, obj, method, *args, **kwargs):
        return getattr(obj, method)(*args, **kwargs)
cache = CallbackCache()


class ConnectionView(common.WWrap):
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
        if self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE and flow.response:
            self.view_response()
        else:
            self.view_request()

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

    def _view_conn_raw(self, content):
        txt = []
        for i in utils.cleanBin(content[:VIEW_CUTOFF]).splitlines():
            txt.append(
                urwid.Text(("text", i))
            )
        self._trailer(len(content), txt)
        return txt

    def _view_conn_binary(self, content):
        txt = []
        for offset, hexa, s in utils.hexdump(content[:VIEW_CUTOFF]):
            txt.append(urwid.Text([
                ("offset", offset),
                " ",
                ("text", hexa),
                "   ",
                ("text", s),
            ]))
        self._trailer(len(content), txt)
        return txt

    def _view_conn_xmlish(self, content):
        txt = []
        for i in utils.pretty_xmlish(content[:VIEW_CUTOFF]):
            txt.append(
                urwid.Text(("text", i)),
            )
        self._trailer(len(content), txt)
        return txt

    def _view_conn_json(self, lines):
        txt = []
        sofar = 0
        for i in lines:
            sofar += len(i)
            txt.append(
                urwid.Text(("text", i)),
            )
            if sofar > VIEW_CUTOFF:
                break
        self._trailer(sum(len(i) for i in lines), txt)
        return txt

    def _view_conn_formdata(self, content, boundary):
        rx = re.compile(r'\bname="([^"]+)"')
        keys = []
        vals = []

        for i in content.split("--" + boundary):
            parts = i.splitlines()
            if len(parts) > 1 and parts[0][0:2] != "--":
                match = rx.search(parts[1])
                if match:
                    keys.append(match.group(1) + ":")
                    vals.append(utils.cleanBin(
                        "\n".join(parts[3+parts[2:].index(""):])
                    ))
        kv = common.format_keyvals(
            zip(keys, vals),
            key = "header",
            val = "text"
        )
        return [
            urwid.Text(("highlight", "Form data:\n")),
            urwid.Text(kv)
        ]

    def _view_conn_urlencoded(self, lines):
        kv = common.format_keyvals(
                [(k+":", v) for (k, v) in lines],
                key = "header",
                val = "text"
             )
        return [
                    urwid.Text(("highlight", "URLencoded data:\n")),
                    urwid.Text(kv)
                ]

    def _find_pretty_view(self, content, hdrItems):
        ctype = None
        for i in hdrItems:
            if i[0].lower() == "content-type":
                ctype = i[1]
                break
        if ctype and "x-www-form-urlencoded" in ctype:
            data = utils.urldecode(content)
            if data:
                return self._view_conn_urlencoded(data)
        if utils.isXML(content):
            return self._view_conn_xmlish(content)
        elif ctype and "application/json" in ctype:
            lines = utils.pretty_json(content)
            if lines:
                return self._view_conn_json(lines)
        elif ctype and "multipart/form-data" in ctype:
            boundary = ctype.split('boundary=')
            if len(boundary) > 1:
                return self._view_conn_formdata(content, boundary[1].split(';')[0])
        return self._view_conn_raw(content)

    def _cached_conn_text(self, e, content, hdrItems, viewmode):
        hdr = []
        hdr.extend(
            common.format_keyvals(
                [(h+":", v) for (h, v) in hdrItems],
                key = "header",
                val = "text"
            )
        )
        hdr.append("\n")

        txt = [urwid.Text(hdr)]
        if content:
            if viewmode == common.VIEW_BODY_HEX:
                txt.extend(self._view_conn_binary(content))
            elif viewmode == common.VIEW_BODY_PRETTY:
                if e:
                    decoded = encoding.decode(e, content)
                    if decoded:
                        content = decoded
                        if e and e != "identity":
                            txt.append(
                                urwid.Text(("highlight", "Decoded %s data:\n"%e))
                            )
                txt.extend(self._find_pretty_view(content, hdrItems))
            else:
                txt.extend(self._view_conn_raw(content))
        return urwid.ListBox(txt)




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
        if active == common.VIEW_FLOW_REQUEST:
            parts.append(self._tab(qt, True))
        else:
            parts.append(self._tab(qt, False))

        if self.flow.intercepting and not self.flow.response.acked:
            st = "Response (intercepted)"
        else:
            st = "Response"
        if active == common.VIEW_FLOW_RESPONSE:
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
        e = conn.headers["content-encoding"]
        e = e[0] if e else None
        return cache.callback(
                    self, "_cached_conn_text",
                    e,
                    conn.content,
                    tuple(tuple(i) for i in conn.headers.lst),
                    viewmode
                )

    def view_request(self):
        self.state.view_flow_mode = common.VIEW_FLOW_REQUEST
        self.master.statusbar.update("Calculating view...")
        body = self._conn_text(
            self.flow.request,
            self.state.view_body_mode
        )
        self.w = self.wrap_body(common.VIEW_FLOW_REQUEST, body)
        self.master.statusbar.update("")

    def view_response(self):
        self.state.view_flow_mode = common.VIEW_FLOW_RESPONSE
        self.master.statusbar.update("Calculating view...")
        if self.flow.response:
            body = self._conn_text(
                self.flow.response,
                self.state.view_body_mode
            )
        else:
            body = urwid.ListBox(
                        [
                            urwid.Text(""),
                            urwid.Text(
                                [
                                    ("highlight", "No response. Press "),
                                    ("key", "e"),
                                    ("highlight", " and edit any aspect to add one."),
                                ]
                            )
                        ]
                   )
        self.w = self.wrap_body(common.VIEW_FLOW_RESPONSE, body)
        self.master.statusbar.update("")

    def refresh_connection(self, c=None):
        if c == self.flow:
            if self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE and self.flow.response:
                self.view_response()
            else:
                self.view_request()

    def edit_method(self, m):
        for i in self.methods:
            if i[1] == m:
                self.flow.request.method = i[0].upper()
        self.master.refresh_connection(self.flow)

    def save_body(self, path):
        if not path:
            return
        self.state.last_saveload = path
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
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
        if not request.set_url(str(url)):
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

    def set_headers(self, lst, conn):
        conn.headers = flow.Headers(lst)

    def edit(self, part):
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            conn = self.flow.request
        else:
            if not self.flow.response:
                self.flow.response = flow.Response(self.flow.request, 200, "OK", flow.Headers(), "")
            conn = self.flow.response

        self.flow.backup()
        if part == "b":
            c = self.master.spawn_editor(conn.content or "")
            conn.content = c.rstrip("\n")
        elif part == "h":
            self.master.view_kveditor("Editing headers", conn.headers.lst, self.set_headers, conn)
        elif part == "u" and self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.master.prompt_edit("URL", conn.get_url(), self.set_url)
        elif part == "m" and self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            self.master.prompt_onekey("Method", self.methods, self.edit_method)
        elif part == "c" and self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Code", str(conn.code), self.set_resp_code)
        elif part == "m" and self.state.view_flow_mode == common.VIEW_FLOW_RESPONSE:
            self.master.prompt_edit("Message", conn.msg, self.set_resp_msg)
        self.master.refresh_connection(self.flow)

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
        self.master.view_flow(new_flow)

    def view_next_flow(self, flow):
        return self._view_nextprev_flow("next", flow)

    def view_prev_flow(self, flow):
        return self._view_nextprev_flow("prev", flow)

    def keypress(self, size, key):
        if key == " ":
            self.view_next_flow(self.flow)
            return key

        key = common.shortcuts(key)
        if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
            conn = self.flow.request
        else:
            conn = self.flow.response

        if key == "q":
            self.master.view_connlist()
            key = None
        elif key == "tab":
            if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
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
            if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
                self.master.prompt_onekey(
                    "Edit request",
                    (
                        ("header", "h"),
                        ("body", "b"),
                        ("url", "u"),
                        ("method", "m"),
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
        elif key == "m":
            self.master.prompt_onekey(
                "View",
                (
                    ("raw", "r"),
                    ("pretty", "p"),
                    ("hex", "h"),
                ),
                self.master.changeview
            )
            key = None
        elif key == "p":
            self.view_prev_flow(self.flow)
        elif key == "r":
            r = self.master.replay_request(self.flow)
            if r:
                self.master.statusbar.message(r)
            self.master.refresh_connection(self.flow)
        elif key == "R":
            self.state.revert(self.flow)
            self.master.refresh_connection(self.flow)
        elif key == "W":
            self.master.path_prompt(
                "Save this flow: ",
                self.state.last_saveload,
                self.master.save_one_flow,
                self.flow
            )
        elif key == "v":
            if conn and conn.content:
                t = conn.headers["content-type"] or [None]
                t = t[0]
                self.master.spawn_external_viewer(conn.content, t)
        elif key == "b":
            if conn:
                if self.state.view_flow_mode == common.VIEW_FLOW_REQUEST:
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
        elif key == "|":
            self.master.path_prompt(
                "Send flow to script: ", self.state.last_script,
                self.master.run_script_once, self.flow
            )
        elif key == "z":
            if conn:
                e = conn.headers["content-encoding"] or ["identity"]
                if e[0] != "identity":
                    conn.decode()
                else:
                    self.master.prompt_onekey(
                        "Select encoding: ",
                        (
                            ("gzip", "z"),
                            ("deflate", "d"),
                        ),
                        self.encode_callback,
                        conn
                    )
                self.master.refresh_connection(self.flow)
        else:
            return key

    def encode_callback(self, key, conn):
        encoding_map = {
            "z": "gzip",
            "d": "deflate",
        }
        conn.encode(encoding_map[key])
        self.master.refresh_connection(self.flow)
