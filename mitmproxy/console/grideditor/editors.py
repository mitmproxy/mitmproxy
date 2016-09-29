from __future__ import absolute_import, print_function, division
import re
import urwid
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy.builtins import script
from mitmproxy.console import common
from mitmproxy.console.grideditor import base
from mitmproxy.console.grideditor import col_bytes
from mitmproxy.console.grideditor import col_text
from mitmproxy.console.grideditor import col_subgrid
from mitmproxy.console import signals
from netlib.http import user_agents


class QueryEditor(base.GridEditor):
    title = "Editing query"
    columns = [
        col_text.Column("Key"),
        col_text.Column("Value")
    ]


class HeaderEditor(base.GridEditor):
    title = "Editing headers"
    columns = [
        col_bytes.Column("Key"),
        col_bytes.Column("Value")
    ]

    def make_help(self):
        h = super(HeaderEditor, self).make_help()
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


class URLEncodedFormEditor(base.GridEditor):
    title = "Editing URL-encoded form"
    columns = [
        col_bytes.Column("Key"),
        col_bytes.Column("Value")
    ]


class ReplaceEditor(base.GridEditor):
    title = "Editing replacement patterns"
    columns = [
        col_text.Column("Filter"),
        col_bytes.Column("Regex"),
        col_bytes.Column("Replacement"),
    ]

    def is_error(self, col, val):
        if col == 0:
            if not flowfilter.parse(val):
                return "Invalid filter specification."
        elif col == 1:
            try:
                re.compile(val)
            except re.error:
                return "Invalid regular expression."
        return False


class SetHeadersEditor(base.GridEditor):
    title = "Editing header set patterns"
    columns = [
        col_text.Column("Filter"),
        col_bytes.Column("Header"),
        col_bytes.Column("Value"),
    ]

    def is_error(self, col, val):
        if col == 0:
            if not flowfilter.parse(val):
                return "Invalid filter specification"
        return False

    def make_help(self):
        h = super(SetHeadersEditor, self).make_help()
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


class PathEditor(base.GridEditor):
    # TODO: Next row on enter?

    title = "Editing URL path components"
    columns = [
        col_text.Column("Component"),
    ]

    def data_in(self, data):
        return [[i] for i in data]

    def data_out(self, data):
        return [i[0] for i in data]


class ScriptEditor(base.GridEditor):
    title = "Editing scripts"
    columns = [
        col_text.Column("Command"),
    ]

    def is_error(self, col, val):
        try:
            script.parse_command(val)
        except exceptions.AddonError as e:
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


class CookieEditor(base.GridEditor):
    title = "Editing request Cookie header"
    columns = [
        col_text.Column("Name"),
        col_text.Column("Value"),
    ]


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


class SetCookieEditor(base.GridEditor):
    title = "Editing response SetCookie header"
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
