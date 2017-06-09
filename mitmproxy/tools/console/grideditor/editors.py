import re

import urwid

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy.addons import script
from mitmproxy.tools.console import common
from mitmproxy.tools.console.grideditor import base
from mitmproxy.tools.console.grideditor import col_text
from mitmproxy.tools.console.grideditor import col_bytes
from mitmproxy.tools.console.grideditor import col_subgrid
from mitmproxy.tools.console import signals
from mitmproxy.net.http import user_agents
from mitmproxy.net.http import Headers


class QueryEditor(base.FocusEditor):
    title = "Edit Query"
    columns = [
        col_text.Column("Key"),
        col_text.Column("Value")
    ]

    def get_data(self, flow):
        return flow.request.query.items(multi=True)

    def set_data(self, vals, flow):
        flow.request.query = vals


class HeaderEditor(base.FocusEditor):
    columns = [
        col_bytes.Column("Key"),
        col_bytes.Column("Value")
    ]

    def make_help(self):
        h = super().make_help()
        text = [
            urwid.Text([("text", "Special keys:\n")])
        ]
        keys = [
            ("U", "add User-Agent header"),
        ]
        text.extend(
            common.format_keyvals(keys, key="key", val="text", indent=4)
        )
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = user_agents.get_by_shortcut(k)
        if ua:
            self.walker.add_value(
                [
                    b"User-Agent",
                    ua[2].encode()
                ]
            )

    def handle_key(self, key):
        if key == "U":
            signals.status_prompt_onekey.send(
                prompt="Add User-Agent header:",
                keys=[(i[0], i[1]) for i in user_agents.UASTRINGS],
                callback=self.set_user_agent,
            )
            return True


class RequestHeaderEditor(HeaderEditor):
    title = "Edit Request Headers"

    def get_data(self, flow):
        return flow.request.headers.fields

    def set_data(self, vals, flow):
        flow.request.headers = Headers(vals)


class ResponseHeaderEditor(HeaderEditor):
    title = "Edit Response Headers"

    def get_data(self, flow):
        return flow.response.headers.fields

    def set_data(self, vals, flow):
        flow.response.headers = Headers(vals)


class RequestFormEditor(base.FocusEditor):
    title = "Edit URL-encoded Form"
    columns = [
        col_text.Column("Key"),
        col_text.Column("Value")
    ]

    def get_data(self, flow):
        return flow.request.urlencoded_form.items(multi=True)

    def set_data(self, vals, flow):
        flow.request.urlencoded_form = vals


class SetHeadersEditor(base.GridEditor):
    title = "Editing header set patterns"
    columns = [
        col_text.Column("Filter"),
        col_text.Column("Header"),
        col_text.Column("Value"),
    ]

    def is_error(self, col, val):
        if col == 0:
            if not flowfilter.parse(val):
                return "Invalid filter specification"
        return False

    def make_help(self):
        h = super().make_help()
        text = [
            urwid.Text([("text", "Special keys:\n")])
        ]
        keys = [
            ("U", "add User-Agent header"),
        ]
        text.extend(
            common.format_keyvals(keys, key="key", val="text", indent=4)
        )
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = user_agents.get_by_shortcut(k)
        if ua:
            self.walker.add_value(
                [
                    ".*",
                    b"User-Agent",
                    ua[2].encode()
                ]
            )

    def handle_key(self, key):
        if key == "U":
            signals.status_prompt_onekey.send(
                prompt="Add User-Agent header:",
                keys=[(i[0], i[1]) for i in user_agents.UASTRINGS],
                callback=self.set_user_agent,
            )
            return True


class PathEditor(base.FocusEditor):
    # TODO: Next row on enter?

    title = "Edit Path Components"
    columns = [
        col_text.Column("Component"),
    ]

    def data_in(self, data):
        return [[i] for i in data]

    def data_out(self, data):
        return [i[0] for i in data]

    def get_data(self, flow):
        return self.data_in(flow.request.path_components)

    def set_data(self, vals, flow):
        flow.request.path_components = self.data_out(vals)


class ScriptEditor(base.GridEditor):
    title = "Editing scripts"
    columns = [
        col_text.Column("Command"),
    ]

    def is_error(self, col, val):
        try:
            script.parse_command(val)
        except exceptions.OptionsError as e:
            return str(e)


class HostPatternEditor(base.GridEditor):
    title = "Editing host patterns"
    columns = [
        col_text.Column("Regex (matched on hostname:port / ip:port)")
    ]

    def is_error(self, col, val):
        try:
            re.compile(val, re.IGNORECASE)
        except re.error as e:
            return "Invalid regex: %s" % str(e)

    def data_in(self, data):
        return [[i] for i in data]

    def data_out(self, data):
        return [i[0] for i in data]


class CookieEditor(base.FocusEditor):
    title = "Edit Cookies"
    columns = [
        col_text.Column("Name"),
        col_text.Column("Value"),
    ]

    def get_data(self, flow):
        return flow.request.cookies.items(multi=True)

    def set_data(self, vals, flow):
        flow.request.cookies = vals


class CookieAttributeEditor(base.GridEditor):
    title = "Editing Set-Cookie attributes"
    columns = [
        col_text.Column("Name"),
        col_text.Column("Value"),
    ]

    def data_in(self, data):
        return [(k, v or "") for k, v in data]

    def data_out(self, data):
        ret = []
        for i in data:
            if not i[1]:
                ret.append([i[0], None])
            else:
                ret.append(i)
        return ret


class SetCookieEditor(base.FocusEditor):
    title = "Edit SetCookie Header"
    columns = [
        col_text.Column("Name"),
        col_text.Column("Value"),
        col_subgrid.Column("Attributes", CookieAttributeEditor),
    ]

    def data_in(self, data):
        flattened = []
        for key, (value, attrs) in data:
            flattened.append([key, value, attrs.items(multi=True)])
        return flattened

    def data_out(self, data):
        vals = []
        for key, value, attrs in data:
            vals.append(
                [
                    key,
                    (value, attrs)
                ]
            )
        return vals

    def get_data(self, flow):
        return self.data_in(flow.response.cookies.items(multi=True))

    def set_data(self, vals, flow):
        flow.response.cookies = self.data_out(vals)


class OptionsEditor(base.GridEditor):
    title = None  # type: str
    columns = [
        col_text.Column("")
    ]

    def __init__(self, master, name, vals):
        self.name = name
        super().__init__(master, [[i] for i in vals], self.callback)

    def callback(self, vals):
        try:
            setattr(self.master.options, self.name, [i[0] for i in vals])
        except exceptions.OptionsError as v:
            signals.status_message.send(message=str(v))

    def is_error(self, col, val):
        pass
