from __future__ import absolute_import, print_function, division

import urwid

from mitmproxy.console import common, searchable
from netlib import human


def maybe_timestamp(base, attr):
    if base is not None and getattr(base, attr):
        return human.format_timestamp_with_milli(getattr(base, attr))
    else:
        return "active"


def flowdetails(state, flow):
    text = []

    cc = flow.client_conn
    sc = flow.server_conn
    req = flow.request
    resp = flow.response

    if sc is not None:
        text.append(urwid.Text([("head", "Server Connection:")]))
        parts = [
            ["Address", repr(sc.address)],
            ["Resolved Address", repr(sc.ip_address)],
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
                        ", ".join(str(x) for x in c.altnames)
                    ]
                )
            text.extend(
                common.format_keyvals(parts, key="key", val="text", indent=4)
            )

    if cc is not None:
        text.append(urwid.Text([("head", "Client Connection:")]))

        parts = [
            ["Address", repr(cc.address)],
        ]

        text.extend(
            common.format_keyvals(parts, key="key", val="text", indent=4)
        )

    parts = []

    if cc is not None and cc.timestamp_start:
        parts.append(
            [
                "Client conn. established",
                maybe_timestamp(cc, "timestamp_start")
            ]
        )
        if cc.ssl_established:
            parts.append(
                [
                    "Client conn. TLS handshake",
                    maybe_timestamp(cc, "timestamp_ssl_setup")
                ]
            )
    if sc is not None and sc.timestamp_start:
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
                    "Server conn. TLS handshake",
                    maybe_timestamp(sc, "timestamp_ssl_setup")
                ]
            )
    if req is not None and req.timestamp_start:
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
    if resp is not None and resp.timestamp_start:
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

    if parts:
        # sort operations by timestamp
        parts = sorted(parts, key=lambda p: p[1])

        text.append(urwid.Text([("head", "Timing:")]))
        text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))
    return searchable.Searchable(state, text)
