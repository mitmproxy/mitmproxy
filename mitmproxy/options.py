from typing import Optional, Sequence

from mitmproxy import optmanager
from mitmproxy.net import tls


CONF_DIR = "~/.mitmproxy"
CONF_BASENAME = "mitmproxy"
LISTEN_PORT = 8080
CONTENT_VIEW_LINES_CUTOFF = 512
KEY_SIZE = 2048


class Options(optmanager.OptManager):

    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.add_option(
            "server", bool, True,
            "Start a proxy server. Enabled by default."
        )
        self.add_option(
            "showhost", bool, False,
            "Use the Host header to construct URLs for display."
        )

        # Proxy options
        self.add_option(
            "add_upstream_certs_to_client_chain", bool, False,
            """
            Add all certificates of the upstream server to the certificate chain
            that will be served to the proxy client, as extras.
            """
        )
        self.add_option(
            "confdir", str, CONF_DIR,
            "Location of the default mitmproxy configuration files."
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
            "allow_hosts", Sequence[str], [],
            "Opposite of --ignore-hosts."
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
            is host specification in the form of "http[s]://host[:port]".
            """
        )
        self.add_option(
            "upstream_cert", bool, True,
            "Connect to upstream server to look up certificate details."
        )

        self.add_option(
            "http2", bool, True,
            "Enable/disable HTTP/2 support. "
            "HTTP/2 support is enabled by default.",
        )
        self.add_option(
            "http2_priority", bool, False,
            """
            PRIORITY forwarding for HTTP/2 connections. Disabled by default to ensure compatibility
            with misbehaving servers.
            """
        )
        self.add_option(
            "websocket", bool, True,
            "Enable/disable WebSocket support. "
            "WebSocket support is enabled by default.",
        )
        self.add_option(
            "rawtcp", bool, False,
            "Enable/disable experimental raw TCP support. TCP connections starting with non-ascii "
            "bytes are treated as if they would match tcp_hosts. The heuristic is very rough, use "
            "with caution. Disabled by default. "
        )

        self.add_option(
            "spoof_source_address", bool, False,
            """
            Use the client's IP for server-side connections. Combine with
            --upstream-bind-address to spoof a fixed source address.
            """
        )
        self.add_option(
            "ssl_version_client", str, "secure",
            """
            Set supported SSL/TLS versions for client connections. SSLv2, SSLv3
            and 'all' are INSECURE. Defaults to secure, which is TLS1.0+.
            """,
            choices=list(tls.VERSION_CHOICES.keys()),
        )
        self.add_option(
            "ssl_version_server", str, "secure",
            """
            Set supported SSL/TLS versions for server connections. SSLv2, SSLv3
            and 'all' are INSECURE. Defaults to secure, which is TLS1.0+.
            """,
            choices=list(tls.VERSION_CHOICES.keys()),
        )
        self.add_option(
            "ssl_insecure", bool, False,
            "Do not verify upstream server SSL/TLS certificates."
        )
        self.add_option(
            "ssl_verify_upstream_trusted_confdir", Optional[str], None,
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
            "content_view_lines_cutoff", int, CONTENT_VIEW_LINES_CUTOFF,
            """
            Flow content view lines limit. Limit is enabled by default to
            speedup flows browsing.
            """
        )
        self.add_option(
            "key_size", int, KEY_SIZE,
            """
            TLS key size for certificates and CA.
            """
        )

        self.update(**kwargs)
