from __future__ import absolute_import
import urwid
from . import common
from .. import utils

footer = [
    ('heading_key', "q"), ":back ",
]

class FlowDetailsView(urwid.ListBox):
    def __init__(self, master, flow, state):
        self.master, self.flow, self.state = master, flow, state
        urwid.ListBox.__init__(
            self,
            self.flowtext()
        )

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "q":
            self.master.statusbar = self.state[0]
            self.master.body = self.state[1]
            self.master.header = self.state[2]
            self.master.make_view()
            return None
        elif key == "?":
            key = None
        return urwid.ListBox.keypress(self, size, key)

    def flowtext(self):
        text = []

        title = urwid.Text("Flow details")
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")
        text.append(title)

        if self.flow.server_conn:
            text.append(urwid.Text([("head", "Server Connection:")]))
            sc = self.flow.server_conn
            parts = [
                ["Address", "%s:%s" % sc.address()],
                ["Start time", utils.format_timestamp(sc.timestamp_start)],
                ["End time", utils.format_timestamp(sc.timestamp_end) if sc.timestamp_end else "active"],
            ]
            text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

            c = self.flow.server_conn.cert
            if c:
                text.append(urwid.Text([("head", "Server Certificate:")]))
                parts = [
                    ["Type", "%s, %s bits"%c.keyinfo],
                    ["SHA1 digest", c.digest("sha1")],
                    ["Valid to", str(c.notafter)],
                    ["Valid from", str(c.notbefore)],
                    ["Serial", str(c.serial)],
                    [
                        "Subject",
                        urwid.BoxAdapter(
                            urwid.ListBox(common.format_keyvals(c.subject, key="highlight", val="text")),
                            len(c.subject)
                        )
                    ],
                    [
                        "Issuer",
                        urwid.BoxAdapter(
                            urwid.ListBox(common.format_keyvals(c.issuer, key="highlight", val="text")),
                            len(c.issuer)
                        )
                    ]
                ]

                if c.altnames:
                    parts.append(
                        [
                            "Alt names",
                            ", ".join(c.altnames)
                        ]
                    )
                text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

        if self.flow.client_conn:
            text.append(urwid.Text([("head", "Client Connection:")]))
            cc = self.flow.client_conn
            parts = [
                ["Address", "%s:%s" % cc.address()],
                ["Start time", utils.format_timestamp(cc.timestamp_start)],
                # ["Requests", "%s"%cc.requestcount],
                ["End time", utils.format_timestamp(cc.timestamp_end) if cc.timestamp_end else "active"],
            ]
            text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

        return text
