from collections.abc import Sequence
from typing import Optional

from mitmproxy import optmanager

CONF_DIR = "~/.mitmproxy"
CONF_BASENAME = "mitmproxy"
CONTENT_VIEW_LINES_CUTOFF = 512
KEY_SIZE = 2048


class Options(optmanager.OptManager):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.add_option(
            "server", bool, True, "Start a proxy server. Enabled by default."
        )
        self.add_option(
            "showhost",
            bool,
            False,
            """Use the Host header to construct URLs for display.

            This option is disabled by default because malicious apps may send misleading host headers to evade
            your analysis. If this is not a concern, enable this options for better flow display.""",
        )
        self.add_option(
            "show_ignored_hosts",
            bool,
            False,
            """
            Record ignored flows in the UI even if we do not perform TLS interception.
            This option will keep ignored flows' contents in memory, which can greatly increase memory usage.
            A future release will fix this issue, record ignored flows by default, and remove this option.
            """,
        )

        # Proxy options
        self.add_option(
            "add_upstream_certs_to_client_chain",
            bool,
            False,
            """
            Add all certificates of the upstream server to the certificate chain
            that will be served to the proxy client, as extras.
            """,
        )
        self.add_option(
            "confdir",
            str,
            CONF_DIR,
            "Location of the default mitmproxy configuration files.",
        )
        self.add_option(
            "certs",
            Sequence[str],
            [],
            """
            SSL certificates of the form "[domain=]path". The domain may include
            a wildcard, and is equal to "*" if not specified. The file at path
            is a certificate in PEM format. If a private key is included in the
            PEM, it is used, else the default key in the conf dir is used. The
            PEM file should contain the full certificate chain, with the leaf
            certificate as the first entry.
            """,
        )
        self.add_option(
            "cert_passphrase",
            Optional[str],
            None,
            """
            Passphrase for decrypting the private key provided in the --cert option.

            Note that passing cert_passphrase on the command line makes your passphrase visible in your system's
            process list. Specify it in config.yaml to avoid this.
            """,
        )
        self.add_option(
            "client_certs", Optional[str], None, "Client certificate file or directory."
        )
        self.add_option(
            "ignore_hosts",
            Sequence[str],
            [],
            """
            Ignore host and forward all traffic without processing it. In
            transparent mode, it is recommended to use an IP address (range),
            not the hostname. In regular mode, only SSL traffic is ignored and
            the hostname should be used. The supplied value is interpreted as a
            regular expression and matched on the ip or the hostname.
            """,
        )
        self.add_option("allow_hosts", Sequence[str], [], "Opposite of --ignore-hosts.")
        self.add_option(
            "listen_host",
            str,
            "",
            "Address to bind proxy server(s) to (may be overridden for individual modes, see `mode`).",
        )
        self.add_option(
            "listen_port",
            Optional[int],
            None,
            "Port to bind proxy server(s) to (may be overridden for individual modes, see `mode`). "
            "By default, the port is mode-specific. The default regular HTTP proxy spawns on port 8080.",
        )
        self.add_option(
            "mode",
            Sequence[str],
            ["regular"],
            """
            The proxy server type(s) to spawn. Can be passed multiple times.

            Mitmproxy supports "regular" (HTTP), "transparent", "socks5", "reverse:SPEC",
            "upstream:SPEC", and "wireguard[:PATH]" proxy servers. For reverse and upstream proxy modes, SPEC
            is host specification in the form of "http[s]://host[:port]". For WireGuard mode, PATH may point to
            a file containing key material. If no such file exists, it will be created on startup.

            You may append `@listen_port` or `@listen_host:listen_port` to override `listen_host` or `listen_port` for
            a specific proxy mode. Features such as client playback will use the first mode to determine
            which upstream server to use.
            """,
        )
        self.add_option(
            "upstream_cert",
            bool,
            True,
            "Connect to upstream server to look up certificate details.",
        )

        self.add_option(
            "http2",
            bool,
            True,
            "Enable/disable HTTP/2 support. HTTP/2 support is enabled by default.",
        )
        self.add_option(
            "http2_ping_keepalive",
            int,
            58,
            """
            Send a PING frame if an HTTP/2 connection is idle for more than
            the specified number of seconds to prevent the remote site from closing it.
            Set to 0 to disable this feature.
            """,
        )
        self.add_option(
            "http3",
            bool,
            True,
            "Enable/disable support for QUIC and HTTP/3. Enabled by default.",
        )
        self.add_option(
            "http_connect_send_host_header",
            bool,
            True,
            "Include host header with CONNECT requests. Enabled by default.",
        )
        self.add_option(
            "websocket",
            bool,
            True,
            "Enable/disable WebSocket support. "
            "WebSocket support is enabled by default.",
        )
        self.add_option(
            "rawtcp",
            bool,
            True,
            "Enable/disable raw TCP connections. "
            "TCP connections are enabled by default. ",
        )
        self.add_option(
            "ssl_insecure",
            bool,
            False,
            """Do not verify upstream server SSL/TLS certificates.

            If this option is enabled, certificate validation is skipped and mitmproxy itself will be vulnerable to
            TLS interception.""",
        )
        self.add_option(
            "ssl_verify_upstream_trusted_confdir",
            Optional[str],
            None,
            """
            Path to a directory of trusted CA certificates for upstream server
            verification prepared using the c_rehash tool.
            """,
        )
        self.add_option(
            "ssl_verify_upstream_trusted_ca",
            Optional[str],
            None,
            "Path to a PEM formatted trusted CA certificate.",
        )
        self.add_option(
            "tcp_hosts",
            Sequence[str],
            [],
            """
            Generic TCP SSL proxy mode for all hosts that match the pattern.
            Similar to --ignore-hosts, but SSL connections are intercepted.
            The communication contents are printed to the log in verbose mode.
            """,
        )
        self.add_option(
            "udp_hosts",
            Sequence[str],
            [],
            """
            Generic UDP SSL proxy mode for all hosts that match the pattern.
            Similar to --ignore-hosts, but SSL connections are intercepted.
            The communication contents are printed to the log in verbose mode.
            """,
        )
        self.add_option(
            "content_view_lines_cutoff",
            int,
            CONTENT_VIEW_LINES_CUTOFF,
            """
            Flow content view lines limit. Limit is enabled by default to
            speedup flows browsing.
            """,
        )
        self.add_option(
            "key_size",
            int,
            KEY_SIZE,
            """
            TLS key size for certificates and CA.
            """,
        )
        self.add_option(
            "protobuf_definitions",
            Optional[str],
            None,
            "Path to a .proto file that's used to resolve Protobuf field names when pretty-printing.",
        )

        self.update(**kwargs)
