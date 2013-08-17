import urwid
import common

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

        if self.flow.response:
            c = self.flow.response.cert
            if c:
                text.append(urwid.Text([("head", "Server Certificate:")]))
                parts = [
                    ["Type", "%s, %s bits"%c.keyinfo],
                    ["SHA1 digest", c.digest("sha1")],
                    ["Valid to", str(c.notafter)],
                    ["Valid from", str(c.notbefore)],
                    ["Serial", str(c.serial)],
                ]

                parts.append(
                    [
                        "Subject",
                        urwid.BoxAdapter(
                            urwid.ListBox(common.format_keyvals(c.subject, key="highlight", val="text")),
                            len(c.subject)
                        )
                    ]
                )

                parts.append(
                    [
                        "Issuer",
                        urwid.BoxAdapter(
                            urwid.ListBox(common.format_keyvals(c.issuer, key="highlight", val="text")),
                            len(c.issuer)
                        )
                    ]
                )

                if c.altnames:
                    parts.append(
                        [
                            "Alt names",
                            ", ".join(c.altnames)
                        ]
                    )
                text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

        if self.flow.request.client_conn:
            text.append(urwid.Text([("head", "Client Connection:")]))
            cc = self.flow.request.client_conn
            parts = [
                ["Address", "%s:%s"%tuple(cc.address)],
                ["Requests", "%s"%cc.requestcount],
                ["Closed", "%s"%cc.close],
            ]
            text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

        return text
