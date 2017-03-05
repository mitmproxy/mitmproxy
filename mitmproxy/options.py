from typing import Tuple, Optional, Sequence, Union

from mitmproxy import optmanager

APP_HOST = "mitm.it"
APP_PORT = 80
CA_DIR = "~/.mitmproxy"
LISTEN_PORT = 8080

# We manually need to specify this, otherwise OpenSSL may select a non-HTTP2 cipher by default.
# https://mozilla.github.io/server-side-tls/ssl-config-generator/?server=apache-2.2.15&openssl=1.0.2&hsts=yes&profile=old
DEFAULT_CLIENT_CIPHERS = "ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:" \
    "ECDHE-ECDSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-DSS-AES128-GCM-SHA256:kEDH+AESGCM:" \
    "ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:" \
    "ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:" \
    "DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-DSS-AES128-SHA256:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:" \
    "DHE-RSA-AES256-SHA:ECDHE-RSA-DES-CBC3-SHA:ECDHE-ECDSA-DES-CBC3-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:" \
    "AES128-SHA256:AES256-SHA256:AES128-SHA:AES256-SHA:AES:DES-CBC3-SHA:" \
    "HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!aECDH:" \
    "!EDH-DSS-DES-CBC3-SHA:!EDH-RSA-DES-CBC3-SHA:!KRB5-DES-CBC3-SHA"


class Options(optmanager.OptManager):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.add_option(
            "onboarding", True, bool,
            "Toggle the mitmproxy onboarding app."
        )
        self.add_option(
            "onboarding_host", APP_HOST, str,
            """
                Domain to serve the onboarding app from. For transparent mode, use
                an IP when a DNS entry for the app domain is not present. Default:
                %s
            """ % APP_HOST
        )
        self.add_option(
            "onboarding_port", APP_PORT, int,
            help="Port to serve the onboarding app from."
        )
        self.add_option(
            "anticache", False, bool,
            """
                Strip out request headers that might cause the server to return
                304-not-modified.
            """
        )
        self.add_option(
            "anticomp", False, bool,
            "Try to convince servers to send us un-compressed data."
        )
        self.add_option("client_replay", [], Sequence[str])
        self.add_option(
            "replay_kill_extra", False, bool,
            "Kill extra requests during replay."
        )
        self.add_option(
            "keepserving", True, bool,
            "Continue serving after client playback or file read."
        )
        self.add_option(
            "no_server", False, bool,
            "Don't start a proxy server."
        )
        self.add_option(
            "server_replay_nopop", False, bool,
            "Disable response pop from response flow. "
            "This makes it possible to replay same response multiple times."
        )
        self.add_option(
            "refresh_server_playback", True, bool,
        )
        self.add_option(
            "rfile", None, Optional[str],
            "Read flows from file."
        )
        self.add_option("scripts", [], Sequence[str])
        self.add_option(
            "showhost", False, bool,
            "Use the Host header to construct URLs for display."
        )
        self.add_option("replacements", [], Sequence[Union[Tuple[str, str, str], str]])
        self.add_option("replacement_files", [], Sequence[Union[Tuple[str, str, str], str]])
        self.add_option("server_replay_use_headers", [], Sequence[str])
        self.add_option("setheaders", [], Sequence[Union[Tuple[str, str, str], str]])
        self.add_option("server_replay", [], Sequence[str])
        self.add_option(
            "stickycookie", None, Optional[str],
            "Set sticky cookie filter. Matched against requests."
        )
        self.add_option(
            "stickyauth", None, Optional[str],
            "Set sticky auth filter. Matched against requests."
        )
        self.add_option(
            "stream_large_bodies", None, Optional[str],
            """
                Stream data to the client if response body exceeds the given
                threshold. If streamed, the body will not be stored in any way.
                Understands k/m/g suffixes, i.e. 3m for 3 megabytes.
            """
        )
        self.add_option(
            "verbosity", 2, int,
            "Log verbosity."
        )
        self.add_option("default_contentview", "auto", str)
        self.add_option("streamfile", None, Optional[str])
        self.add_option("streamfile_append", False, bool)
        self.add_option(
            "server_replay_ignore_content", False, bool,
            "Ignore request's content while searching for a saved flow to replay."
        )
        self.add_option("server_replay_ignore_params", [], Sequence[str])
        self.add_option("server_replay_ignore_payload_params", [], Sequence[str])
        self.add_option(
            "server_replay_ignore_host", False, bool,
            "Ignore request's destination host while searching for a saved"
            " flow to replay"
        )

        # Proxy options
        self.add_option(
            "auth_nonanonymous", False, bool,
            "Allow access to any user long as a credentials are specified."
        )
        self.add_option(
            "auth_singleuser", None, Optional[str],
            """
                Allows access to a a single user, specified in the form
                username:password.
            """
        )
        self.add_option(
            "auth_htpasswd", None, Optional[str],
            "Allow access to users specified in an Apache htpasswd file."
        )
        self.add_option(
            "add_upstream_certs_to_client_chain", False, bool,
            "Add all certificates of the upstream server to the certificate chain "
            "that will be served to the proxy client, as extras."
        )
        self.add_option(
            "body_size_limit", None, Optional[str],
            "Byte size limit of HTTP request and response bodies."
            " Understands k/m/g suffixes, i.e. 3m for 3 megabytes."
        )
        self.add_option(
            "cadir", CA_DIR, str,
            "Location of the default mitmproxy CA files. (%s)" % CA_DIR
        )
        self.add_option("certs", [], Sequence[Tuple[str, str]])
        self.add_option(
            "ciphers_client", DEFAULT_CLIENT_CIPHERS, str,
            "Set supported ciphers for client connections. (OpenSSL Syntax)"
        )
        self.add_option(
            "ciphers_server", None, Optional[str],
            "Set supported ciphers for server connections. (OpenSSL Syntax)"
        )
        self.add_option(
            "client_certs", None, Optional[str],
            "Client certificate file or directory."
        )
        self.add_option("ignore_hosts", [], Sequence[str])
        self.add_option(
            "listen_host", "", str,
            "Address to bind proxy to (defaults to all interfaces)"
        )
        self.add_option(
            "listen_port", LISTEN_PORT, int,
            "Proxy service port."
        )
        self.add_option(
            "upstream_bind_address", "", str,
            "Address to bind upstream requests to (defaults to none)"
        )
        self.add_option("mode", "regular", str)
        self.add_option(
            "upstream_cert", True, bool,
            "Connect to upstream server to look up certificate details."
        )
        self.add_option(
            "keep_host_header", False, bool,
            "Reverse Proxy: Keep the original host header instead of rewriting it"
            " to the reverse proxy target."
        )

        self.add_option(
            "http2", True, bool,
            "Enable/disable HTTP/2 support. "
            "HTTP/2 support is enabled by default.",
        )
        self.add_option(
            "http2_priority", False, bool,
            "Enable/disable PRIORITY forwarding for HTTP/2 connections. "
            "PRIORITY forwarding is disabled by default, "
            "because some webservers fail to implement the RFC properly.",
        )
        self.add_option(
            "websocket", True, bool,
            "Enable/disable WebSocket support. "
            "WebSocket support is enabled by default.",
        )
        self.add_option(
            "rawtcp", False, bool,
            "Enable/disable experimental raw TCP support. "
            "Disabled by default. "
        )

        self.add_option(
            "spoof_source_address", False, bool,
            "Use the client's IP for server-side connections. "
            "Combine with --upstream-bind-address to spoof a fixed source address."
        )
        self.add_option("upstream_server", None, Optional[str])
        self.add_option(
            "upstream_auth", None, Optional[str],
            """
                Add HTTP Basic authentcation to upstream proxy and reverse proxy
                requests. Format: username:password
            """
        )
        self.add_option("ssl_version_client", "secure", str)
        self.add_option("ssl_version_server", "secure", str)
        self.add_option(
            "ssl_insecure", False, bool,
            "Do not verify upstream server SSL/TLS certificates."
        )
        self.add_option(
            "ssl_verify_upstream_trusted_cadir", None, Optional[str],
            "Path to a directory of trusted CA certificates for upstream "
            "server verification prepared using the c_rehash tool."
        )
        self.add_option(
            "ssl_verify_upstream_trusted_ca", None, Optional[str],
            "Path to a PEM formatted trusted CA certificate."
        )
        self.add_option("tcp_hosts", [], Sequence[str])

        self.add_option(
            "intercept", None, Optional[str],
            "Intercept filter expression."
        )

        # Console options
        self.add_option(
            "console_eventlog", False, bool,
            "Show event log."
        )
        self.add_option(
            "console_focus_follow", False, bool,
            "Focus follows new flows."
        )
        self.add_option("console_palette", "dark", Optional[str])
        self.add_option(
            "console_palette_transparent", False, bool,
            "Set transparent background for palette."
        )
        self.add_option(
            "console_mouse", True, bool,
            "Console mouse interaction."
        )
        self.add_option("console_order", None, Optional[str])
        self.add_option(
            "console_order_reversed", False, bool,
        )

        self.add_option(
            "filter", None, Optional[str],
            "Filter view expression."
        )

        # Web options
        self.add_option(
            "web_open_browser", True, bool,
            "Start a browser"
        )
        self.add_option(
            "web_debug", False, bool,
            "Mitmweb debugging"
        )
        self.add_option(
            "web_port", 8081, int,
            "Mitmweb port."
        )
        self.add_option(
            "web_iface", "127.0.0.1", str,
            "Mitmweb interface."
        )

        # Dump options
        self.add_option("filtstr", None, Optional[str])
        self.add_option(
            "flow_detail", 1, int,
            "Flow detail display level"
        )

        self.update(**kwargs)
