from typing import Optional, Sequence

from mitmproxy import optmanager
from mitmproxy import contentviews
from mitmproxy.net import tcp

# We redefine these here for now to avoid importing Urwid-related guff on
# platforms that don't support it, and circular imports. We can do better using
# a lazy checker down the track.
console_palettes = [
    "lowlight",
    "lowdark",
    "light",
    "dark",
    "solarized_light",
    "solarized_dark"
]
view_orders = [
    "time",
    "method",
    "url",
    "size",
]

APP_HOST = "mitm.it"
APP_PORT = 80
CA_DIR = "~/.mitmproxy"
LISTEN_PORT = 8080

# Some help text style guidelines:
#
# - Should be a single paragraph with no linebreaks. Help will be reflowed by
# tools.
# - Avoid adding information about the data type - we can generate that.


class Options(optmanager.OptManager):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.add_option(
            "onboarding", bool, True,
            "Toggle the mitmproxy onboarding app."
        )
        self.add_option(
            "onboarding_host", str, APP_HOST,
            """
            Onboarding app domain. For transparent mode, use an IP when a DNS
            entry for the app domain is not present.
            """
        )
        self.add_option(
            "onboarding_port", int, APP_PORT,
            "Port to serve the onboarding app from."
        )
        self.add_option(
            "anticache", bool, False,
            """
            Strip out request headers that might cause the server to return
            304-not-modified.
            """
        )
        self.add_option(
            "anticomp", bool, False,
            "Try to convince servers to send us un-compressed data."
        )
        self.add_option(
            "client_replay", Sequence[str], [],
            "Replay client requests from a saved file."
        )
        self.add_option(
            "replay_kill_extra", bool, False,
            "Kill extra requests during replay."
        )
        self.add_option(
            "keepserving", bool, False,
            """
            Continue serving after client playback, server playback or file
            read. This option is ignored by interactive tools, which always keep
            serving.
            """
        )
        self.add_option(
            "server", bool, True,
            "Start a proxy server."
        )
        self.add_option(
            "server_replay_nopop", bool, False,
            """
            Don't remove flows from server replay state after use. This makes it
            possible to replay same response multiple times.
            """
        )
        self.add_option(
            "refresh_server_playback", bool, True,
            """
            Refresh server replay responses by adjusting date, expires and
            last-modified headers, as well as adjusting cookie expiration.
            """
        )
        self.add_option(
            "rfile", Optional[str], None,
            "Read flows from file."
        )
        self.add_option(
            "scripts", Sequence[str], [],
            """
            Execute a script.
            """
        )
        self.add_option(
            "showhost", bool, False,
            "Use the Host header to construct URLs for display."
        )
        self.add_option(
            "replacements", Sequence[str], [],
            """
            Replacement patterns of the form "/pattern/regex/replacement", where
            the separator can be any character.
            """
        )
        self.add_option(
            "server_replay_use_headers", Sequence[str], [],
            "Request headers to be considered during replay."
        )
        self.add_option(
            "setheaders", Sequence[str], [],
            """
            Header set pattern of the form "/pattern/header/value", where the
            separator can be any character.
            """
        )
        self.add_option(
            "server_replay", Sequence[str], [],
            "Replay server responses from a saved file."
        )
        self.add_option(
            "stickycookie", Optional[str], None,
            "Set sticky cookie filter. Matched against requests."
        )
        self.add_option(
            "stickyauth", Optional[str], None,
            "Set sticky auth filter. Matched against requests."
        )
        self.add_option(
            "stream_large_bodies", Optional[str], None,
            """
            Stream data to the client if response body exceeds the given
            threshold. If streamed, the body will not be stored in any way.
            Understands k/m/g suffixes, i.e. 3m for 3 megabytes.
            """
        )
        self.add_option(
            "verbosity", int, 2,
            "Log verbosity."
        )
        self.add_option(
            "default_contentview", str, "auto",
            "The default content view mode.",
            choices = [i.name for i in contentviews.views]
        )
        self.add_option(
            "streamfile", Optional[str], None,
            "Write flows to file. Prefix path with + to append."
        )
        self.add_option(
            "streamfile_filter", Optional[str], None,
            "Filter which flows are written to file."
        )
        self.add_option(
            "server_replay_ignore_content", bool, False,
            "Ignore request's content while searching for a saved flow to replay."
        )
        self.add_option(
            "server_replay_ignore_params", Sequence[str], [],
            """
            Request's parameters to be ignored while searching for a saved flow
            to replay.
            """
        )
        self.add_option(
            "server_replay_ignore_payload_params", Sequence[str], [],
            """
            Request's payload parameters (application/x-www-form-urlencoded or
            multipart/form-data) to be ignored while searching for a saved flow
            to replay.
            """
        )
        self.add_option(
            "server_replay_ignore_host", bool, False,
            """
            Ignore request's destination host while searching for a saved flow
            to replay.
            """
        )

        # Proxy options
        self.add_option(
            "proxyauth", Optional[str], None,
            """
            Require proxy authentication. Value may be "any" to require
            authenticaiton but accept any credentials, start with "@" to specify
            a path to an Apache htpasswd file, or be of the form
            "username:password".
            """
        )
        self.add_option(
            "add_upstream_certs_to_client_chain", bool, False,
            """
            Add all certificates of the upstream server to the certificate chain
            that will be served to the proxy client, as extras.
            """
        )
        self.add_option(
            "body_size_limit", Optional[str], None,
            """
            Byte size limit of HTTP request and response bodies. Understands
            k/m/g suffixes, i.e. 3m for 3 megabytes.
            """
        )
        self.add_option(
            "cadir", str, CA_DIR,
            "Location of the default mitmproxy CA files."
        )
        self.add_option(
            "certs", Sequence[str], [],
            """
            SSL certificates of the form "[domain=]path". The domain may include
            a wildcard, and is equal to "*" if not specified. The file at path
            is a certificate in PEM format. If a private key is included in the
            PEM, it is used, else the default key in the conf dir is used. The
            PEM file should contain the full certificate chain, with the leaf
            certificate as the first entry.
            """
        )
        self.add_option(
            "ciphers_client", Optional[str], None,
            "Set supported ciphers for client connections using OpenSSL syntax."
        )
        self.add_option(
            "ciphers_server", Optional[str], None,
            "Set supported ciphers for server connections using OpenSSL syntax."
        )
        self.add_option(
            "client_certs", Optional[str], None,
            "Client certificate file or directory."
        )
        self.add_option(
            "ignore_hosts", Sequence[str], [],
            """
            Ignore host and forward all traffic without processing it. In
            transparent mode, it is recommended to use an IP address (range),
            not the hostname. In regular mode, only SSL traffic is ignored and
            the hostname should be used. The supplied value is interpreted as a
            regular expression and matched on the ip or the hostname.
            """
        )
        self.add_option(
            "listen_host", str, "",
            "Address to bind proxy to."
        )
        self.add_option(
            "listen_port", int, LISTEN_PORT,
            "Proxy service port."
        )
        self.add_option(
            "upstream_bind_address", str, "",
            "Address to bind upstream requests to."
        )
        self.add_option(
            "mode", str, "regular",
            """
            Mode can be "regular", "transparent", "socks5", "reverse:SPEC",
            or "upstream:SPEC". For reverse and upstream proxy modes, SPEC
            is proxy specification in the form of "http[s]://host[:port]".
            """
        )
        self.add_option(
            "upstream_cert", bool, True,
            "Connect to upstream server to look up certificate details."
        )
        self.add_option(
            "keep_host_header", bool, False,
            """
            Reverse Proxy: Keep the original host header instead of rewriting it
            to the reverse proxy target.
            """
        )

        self.add_option(
            "http2", bool, True,
            "Enable/disable HTTP/2 support. "
            "HTTP/2 support is enabled by default.",
        )
        self.add_option(
            "http2_priority", bool, False,
            """
            PRIORITY forwarding for HTTP/2 connections. PRIORITY forwarding is
            disabled by default, because some webservers fail to implement the
            RFC properly.
            """
        )
        self.add_option(
            "websocket", bool, True,
            "Enable/disable WebSocket support. "
            "WebSocket support is enabled by default.",
        )
        self.add_option(
            "rawtcp", bool, False,
            "Enable/disable experimental raw TCP support. "
            "Disabled by default. "
        )

        self.add_option(
            "spoof_source_address", bool, False,
            """
            Use the client's IP for server-side connections. Combine with
            --upstream-bind-address to spoof a fixed source address.
            """
        )
        self.add_option(
            "upstream_auth", Optional[str], None,
            """
            Add HTTP Basic authentcation to upstream proxy and reverse proxy
            requests. Format: username:password.
            """
        )
        self.add_option(
            "ssl_version_client", str, "secure",
            """
            Set supported SSL/TLS versions for client connections. SSLv2, SSLv3
            and 'all' are INSECURE. Defaults to secure, which is TLS1.0+.
            """,
            choices=list(tcp.sslversion_choices.keys()),
        )
        self.add_option(
            "ssl_version_server", str, "secure",
            """
            Set supported SSL/TLS versions for server connections. SSLv2, SSLv3
            and 'all' are INSECURE. Defaults to secure, which is TLS1.0+.
            """,
            choices=list(tcp.sslversion_choices.keys()),
        )
        self.add_option(
            "ssl_insecure", bool, False,
            "Do not verify upstream server SSL/TLS certificates."
        )
        self.add_option(
            "ssl_verify_upstream_trusted_cadir", Optional[str], None,
            """
            Path to a directory of trusted CA certificates for upstream server
            verification prepared using the c_rehash tool.
            """
        )
        self.add_option(
            "ssl_verify_upstream_trusted_ca", Optional[str], None,
            "Path to a PEM formatted trusted CA certificate."
        )
        self.add_option(
            "tcp_hosts", Sequence[str], [],
            """
            Generic TCP SSL proxy mode for all hosts that match the pattern.
            Similar to --ignore, but SSL connections are intercepted. The
            communication contents are printed to the log in verbose mode.
            """
        )

        self.add_option(
            "intercept", Optional[str], None,
            "Intercept filter expression."
        )

        # Console options
        self.add_option(
            "console_eventlog", bool, False,
            "Show event log."
        )
        self.add_option(
            "console_focus_follow", bool, False,
            "Focus follows new flows."
        )
        self.add_option(
            "console_palette", str, "dark",
            "Color palette.",
            choices=sorted(console_palettes),
        )
        self.add_option(
            "console_palette_transparent", bool, False,
            "Set transparent background for palette."
        )
        self.add_option(
            "console_mouse", bool, True,
            "Console mouse interaction."
        )
        self.add_option(
            "console_order", str, "time",
            "Flow sort order.",
            choices=view_orders,
        )
        self.add_option(
            "console_order_reversed", bool, False,
            "Reverse the sorting order."
        )

        self.add_option(
            "view_filter", Optional[str], None,
            "Limit which flows are displayed."
        )

        # Web options
        self.add_option(
            "web_open_browser", bool, True,
            "Start a browser."
        )
        self.add_option(
            "web_debug", bool, False,
            "Mitmweb debugging."
        )
        self.add_option(
            "web_port", int, 8081,
            "Mitmweb port."
        )
        self.add_option(
            "web_iface", str, "127.0.0.1",
            "Mitmweb interface."
        )

        # Dump options
        self.add_option(
            "flow_detail", int, 1,
            "Flow detail display level."
        )

        self.update(**kwargs)
