from __future__ import absolute_import
import urwid
from . import common, searchable
from .. import utils


def maybe_timestamp(base, attr):
    if base and getattr(base, attr):
        return utils.format_timestamp_with_milli(getattr(base, attr))
    else:
        return "active"
    pass


def flowdetails(state, flow):
    text = []

    cc = flow.client_conn
    sc = flow.server_conn
    req = flow.request
    resp = flow.response

    if sc:
        text.append(urwid.Text([("head", "Server Connection:")]))
        parts = [
            ["Address", "%s:%s" % sc.address()],
        ]

        text.extend(
            common.format_keyvals(parts, key="key", val="text", indent=4)
        )

        c = sc.cert
        if c:
            text.append(urwid.Text([("head", "Server Certificate:")]))
            parts = [
                ["Type", "%s, %s bits" % c.keyinfo],
                ["SHA1 digest", c.digest("sha1")],
                ["Valid to", str(c.notafter)],
                ["Valid from", str(c.notbefore)],
                ["Serial", str(c.serial)],
                [
                    "Subject",
                    urwid.BoxAdapter(
                        urwid.ListBox(
                            common.format_keyvals(
                                c.subject,
                                key="highlight",
                                val="text"
                            )
                        ),
                        len(c.subject)
                    )
                ],
                [
                    "Issuer",
                    urwid.BoxAdapter(
                        urwid.ListBox(
                            common.format_keyvals(
                                c.issuer, key="highlight", val="text"
                            )
                        ),
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
            text.extend(
                common.format_keyvals(parts, key="key", val="text", indent=4)
            )

    if cc:
        text.append(urwid.Text([("head", "Client Connection:")]))

        parts = [
            ["Address", "%s:%s" % cc.address()],
            # ["Requests", "%s"%cc.requestcount],
        ]

        text.extend(
            common.format_keyvals(parts, key="key", val="text", indent=4)
        )

    parts = []

    parts.append(
        [
            "Client conn. established",
            maybe_timestamp(cc, "timestamp_start")
        ]
    )
    parts.append(
        [
            "Server conn. initiated",
            maybe_timestamp(sc, "timestamp_start")
        ]
    )
    parts.append(
        [
            "Server conn. TCP handshake",
            maybe_timestamp(sc, "timestamp_tcp_setup")
        ]
    )
    if sc.ssl_established:
        parts.append(
            [
                "Server conn. SSL handshake",
                maybe_timestamp(sc, "timestamp_ssl_setup")
            ]
        )
        parts.append(
            [
                "Client conn. SSL handshake",
                maybe_timestamp(cc, "timestamp_ssl_setup")
            ]
        )
    parts.append(
        [
            "First request byte",
            maybe_timestamp(req, "timestamp_start")
        ]
    )
    parts.append(
        [
            "Request complete",
            maybe_timestamp(req, "timestamp_end")
        ]
    )
    parts.append(
        [
            "First response byte",
            maybe_timestamp(resp, "timestamp_start")
        ]
    )
    parts.append(
        [
            "Response complete",
            maybe_timestamp(resp, "timestamp_end")
        ]
    )

    # sort operations by timestamp
    parts = sorted(parts, key=lambda p: p[1])

    text.append(urwid.Text([("head", "Timing:")]))
    text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))
    return searchable.Searchable(state, text)
