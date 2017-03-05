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
        self.add_option("onboarding", True, bool)
        self.add_option("onboarding_host", APP_HOST, str)
        self.add_option("onboarding_port", APP_PORT, int)
        self.add_option("anticache", False, bool)
        self.add_option("anticomp", False, bool)
        self.add_option("client_replay", [], Sequence[str])
        self.add_option("replay_kill_extra", False, bool)
        self.add_option("keepserving", True, bool)
        self.add_option("no_server", False, bool)
        self.add_option("server_replay_nopop", False, bool)
        self.add_option("refresh_server_playback", True, bool)
        self.add_option("rfile", None, Optional[str])
        self.add_option("scripts", [], Sequence[str])
        self.add_option("showhost", False, bool)
        self.add_option("replacements", [], Sequence[Union[Tuple[str, str, str], str]])
        self.add_option("replacement_files", [], Sequence[Union[Tuple[str, str, str], str]])
        self.add_option("server_replay_use_headers", [], Sequence[str])
        self.add_option("setheaders", [], Sequence[Union[Tuple[str, str, str], str]])
        self.add_option("server_replay", [], Sequence[str])
        self.add_option("stickycookie", None, Optional[str])
        self.add_option("stickyauth", None, Optional[str])
        self.add_option("stream_large_bodies", None, Optional[int])
        self.add_option("verbosity", 2, int)
        self.add_option("default_contentview", "auto", str)
        self.add_option("streamfile", None, Optional[str])
        self.add_option("streamfile_append", False, bool)
        self.add_option("server_replay_ignore_content", False, bool)
        self.add_option("server_replay_ignore_params", [], Sequence[str])
        self.add_option("server_replay_ignore_payload_params", [], Sequence[str])
        self.add_option("server_replay_ignore_host", False, bool)

        # Proxy options
        self.add_option("auth_nonanonymous", False, bool)
        self.add_option("auth_singleuser", None, Optional[str])
        self.add_option("auth_htpasswd", None, Optional[str])
        self.add_option("add_upstream_certs_to_client_chain", False, bool)
        self.add_option("body_size_limit", None, Optional[int])
        self.add_option("cadir", CA_DIR, str)
        self.add_option("certs", [], Sequence[Tuple[str, str]])
        self.add_option("ciphers_client", DEFAULT_CLIENT_CIPHERS, str)
        self.add_option("ciphers_server", None, Optional[str])
        self.add_option("clientcerts", None, Optional[str])
        self.add_option("ignore_hosts", [], Sequence[str])
        self.add_option("listen_host", "", str)
        self.add_option("listen_port", LISTEN_PORT, int)
        self.add_option("upstream_bind_address", "", str)
        self.add_option("mode", "regular", str)
        self.add_option("no_upstream_cert", False, bool)
        self.add_option("keep_host_header", False, bool)

        self.add_option("http2", True, bool)
        self.add_option("http2_priority", False, bool)
        self.add_option("websocket", True, bool)
        self.add_option("rawtcp", False, bool)

        self.add_option("spoof_source_address", False, bool)
        self.add_option("upstream_server", None, Optional[str])
        self.add_option("upstream_auth", None, Optional[str])
        self.add_option("ssl_version_client", "secure", str)
        self.add_option("ssl_version_server", "secure", str)
        self.add_option("ssl_insecure", False, bool)
        self.add_option("ssl_verify_upstream_trusted_cadir", None, Optional[str])
        self.add_option("ssl_verify_upstream_trusted_ca", None, Optional[str])
        self.add_option("tcp_hosts", [], Sequence[str])

        self.add_option("intercept", None, Optional[str])

        # Console options
        self.add_option("console_eventlog", False, bool)
        self.add_option("console_focus_follow", False, bool)
        self.add_option("console_palette", "dark", Optional[str])
        self.add_option("console_palette_transparent", False, bool)
        self.add_option("console_no_mouse", False, bool)
        self.add_option("console_order", None, Optional[str])
        self.add_option("console_order_reversed", False, bool)

        self.add_option("filter", None, Optional[str])

        # Web options
        self.add_option("web_open_browser", True, bool)
        self.add_option("web_debug", False, bool)
        self.add_option("web_port", 8081, int)
        self.add_option("web_iface", "127.0.0.1", str)

        # Dump options
        self.add_option("filtstr", None, Optional[str])
        self.add_option("flow_detail", 1, int)

        self.update(**kwargs)
