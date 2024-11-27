import urwid

import mitmproxy.flow
from mitmproxy import http
from mitmproxy.tools.console import common
from mitmproxy.tools.console import searchable
from mitmproxy.utils import human
from mitmproxy.utils import strutils


def maybe_timestamp(base, attr):
    if base is not None and getattr(base, attr):
        return human.format_timestamp_with_milli(getattr(base, attr))
    else:
        # in mitmdump we serialize before a connection is closed.
        # loading those flows at a later point shouldn't display "active".
        # We also use a ndash (and not a regular dash) so that it is sorted
        # after other timestamps. We may need to revisit that in the future if it turns out
        # to render ugly in consoles.
        return "–"


def flowdetails(state, flow: mitmproxy.flow.Flow):
    text = []

    sc = flow.server_conn
    cc = flow.client_conn
    req: http.Request | None
    resp: http.Response | None
    if isinstance(flow, http.HTTPFlow):
        req = flow.request
        resp = flow.response
    else:
        req = None
        resp = None
    metadata = flow.metadata
    comment = flow.comment

    if comment:
        text.append(urwid.Text([("head", "Comment: "), ("text", comment)]))

    if metadata is not None and len(metadata) > 0:
        parts = [(str(k), repr(v)) for k, v in metadata.items()]
        text.append(urwid.Text([("head", "Metadata:")]))
        text.extend(common.format_keyvals(parts, indent=4))

    if sc is not None and sc.peername:
        text.append(urwid.Text([("head", "Server Connection:")]))
        parts = [
            ("Address", human.format_address(sc.address)),
        ]
        if sc.peername:
            parts.append(("Resolved Address", human.format_address(sc.peername)))
        if resp:
            parts.append(("HTTP Version", resp.http_version))
        if sc.alpn:
            parts.append(("ALPN", strutils.bytes_to_escaped_str(sc.alpn)))

        text.extend(common.format_keyvals(parts, indent=4))

        if sc.certificate_list:
            c = sc.certificate_list[0]
            text.append(urwid.Text([("head", "Server Certificate:")]))
            parts = [
                ("Type", "%s, %s bits" % c.keyinfo),
                ("SHA256 digest", c.fingerprint().hex(" ")),
                ("Valid from", str(c.notbefore)),
                ("Valid to", str(c.notafter)),
                ("Serial", str(c.serial)),
                (
                    "Subject",
                    urwid.Pile(
                        common.format_keyvals(c.subject, key_format="highlight")
                    ),
                ),
                (
                    "Issuer",
                    urwid.Pile(common.format_keyvals(c.issuer, key_format="highlight")),
                ),
            ]

            if c.altnames:
                parts.append(("Alt names", ", ".join(str(x.value) for x in c.altnames)))
            text.extend(common.format_keyvals(parts, indent=4))

    if cc is not None:
        text.append(urwid.Text([("head", "Client Connection:")]))

        parts = [
            ("Address", human.format_address(cc.peername)),
        ]
        if req:
            parts.append(("HTTP Version", req.http_version))
        if cc.tls_version:
            parts.append(("TLS Version", cc.tls_version))
        if cc.sni:
            parts.append(("Server Name Indication", cc.sni))
        if cc.cipher:
            parts.append(("Cipher Name", cc.cipher))
        if cc.alpn:
            parts.append(("ALPN", strutils.bytes_to_escaped_str(cc.alpn)))

        text.extend(common.format_keyvals(parts, indent=4))

    parts = []

    if cc is not None and cc.timestamp_start:
        parts.append(
            ("Client conn. established", maybe_timestamp(cc, "timestamp_start"))
        )
        if cc.tls_established:
            parts.append(
                (
                    "Client conn. TLS handshake",
                    maybe_timestamp(cc, "timestamp_tls_setup"),
                )
            )
        parts.append(("Client conn. closed", maybe_timestamp(cc, "timestamp_end")))

    if sc is not None and sc.timestamp_start:
        parts.append(("Server conn. initiated", maybe_timestamp(sc, "timestamp_start")))
        parts.append(
            ("Server conn. TCP handshake", maybe_timestamp(sc, "timestamp_tcp_setup"))
        )
        if sc.tls_established:
            parts.append(
                (
                    "Server conn. TLS handshake",
                    maybe_timestamp(sc, "timestamp_tls_setup"),
                )
            )
        parts.append(("Server conn. closed", maybe_timestamp(sc, "timestamp_end")))

    if req is not None and req.timestamp_start:
        parts.append(("First request byte", maybe_timestamp(req, "timestamp_start")))
        parts.append(("Request complete", maybe_timestamp(req, "timestamp_end")))

    if resp is not None and resp.timestamp_start:
        parts.append(("First response byte", maybe_timestamp(resp, "timestamp_start")))
        parts.append(("Response complete", maybe_timestamp(resp, "timestamp_end")))

    if parts:
        # sort operations by timestamp
        parts = sorted(parts, key=lambda p: p[1])

        text.append(urwid.Text([("head", "Timing:")]))
        text.extend(common.format_keyvals(parts, indent=4))

    return searchable.Searchable(text)
