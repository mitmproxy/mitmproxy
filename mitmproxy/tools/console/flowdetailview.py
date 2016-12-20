import urwid

from mitmproxy.tools.console import common, searchable
from mitmproxy.utils import human
from mitmproxy.utils import strutils


def maybe_timestamp(base, attr):
    if base is not None and getattr(base, attr):
        return human.format_timestamp_with_milli(getattr(base, attr))
    else:
        return "active"


def flowdetails(state, flow):
    text = []

    sc = flow.server_conn
    cc = flow.client_conn
    req = flow.request
    resp = flow.response
    metadata = flow.metadata

    if metadata is not None and len(metadata.items()) > 0:
        parts = [[str(k), repr(v)] for k, v in metadata.items()]
        text.append(urwid.Text([("head", "Metadata:")]))
        text.extend(common.format_keyvals(parts, key="key", val="text", indent=4))

    if sc is not None:
        text.append(urwid.Text([("head", "Server Connection:")]))
        parts = [
            ["Address", repr(sc.address)],
            ["Resolved Address", repr(sc.ip_address)],
        ]
        if sc.alpn_proto_negotiated:
            parts.append(["ALPN", sc.alpn_proto_negotiated])

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
                        ", ".join(strutils.bytes_to_escaped_str(x) for x in c.altnames)
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
        if cc.tls_version:
            parts.append(["TLS Version", cc.tls_version])
        if cc.sni:
            parts.append(["Server Name Indication", cc.sni])
        if cc.cipher_name:
            parts.append(["Cipher Name", cc.cipher_name])
        if cc.alpn_proto_negotiated:
            parts.append(["ALPN", cc.alpn_proto_negotiated])

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
