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

        cc = self.flow.client_conn
        sc = self.flow.server_conn
        req = self.flow.request;
        resp = self.flow.response;        

        timing_parts = []
        if cc:
            timing_parts.append(["Client conn. established", utils.format_timestamp_with_milli(cc.timestamp_start) if cc.timestamp_start else "active"])
        if sc:
            timing_parts.append(["Server conn. initiated", utils.format_timestamp_with_milli(sc.timestamp_start)])
            timing_parts.append(["Server conn. TCP handshake", utils.format_timestamp_with_milli(sc.timestamp_tcp_setup) if sc.timestamp_tcp_setup else "active"])
            if sc.ssl_established:
                timing_parts.append(["Server conn. SSL handshake", utils.format_timestamp_with_milli(sc.timestamp_ssl_setup) if sc.timestamp_ssl_setup else "active"])

        if cc and sc.ssl_established:
            timing_parts.append(["Client conn. SSL handshake", utils.format_timestamp_with_milli(cc.timestamp_ssl_setup) if cc.timestamp_ssl_setup else "active"])

        timing_parts.append(["First request byte", utils.format_timestamp_with_milli(req.timestamp_start)])
        timing_parts.append(["Request complete", utils.format_timestamp_with_milli(req.timestamp_end) if req.timestamp_end else "active"])

        if resp:
            timing_parts.append(["First response byte", utils.format_timestamp_with_milli(resp.timestamp_start)])
            timing_parts.append(["response complete", utils.format_timestamp_with_milli(resp.timestamp_end) if resp.timestamp_end else "active"])

        if sc:
            text.append(urwid.Text([("head", "Server Connection:")]))
            parts = [
                ["Address", "%s:%s" % sc.address()],
            ]
            
            text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

            c = sc.cert
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

        if cc:
            text.append(urwid.Text([("head", "Client Connection:")]))

            parts = [
                ["Address", "%s:%s" % cc.address()],
                # ["Requests", "%s"%cc.requestcount],
            ]
   
            text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))
            
        text.append(urwid.Text([("head", "Timing:")]))
        text.extend(common.format_keyvals(timing_parts, key="key", val="text", indent=4))
        return text
