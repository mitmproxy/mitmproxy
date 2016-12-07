from typing import Tuple, Optional, Sequence

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
    def __init__(
            self,
            *,  # all args are keyword-only.
            # TODO: rename to onboarding_app_*
            app: bool = True,
            app_host: str = APP_HOST,
            app_port: int = APP_PORT,
            anticache: bool = False,
            anticomp: bool = False,
            client_replay: Sequence[str] = [],
            replay_kill_extra: bool = False,
            keepserving: bool = True,
            no_server: bool = False,
            server_replay_nopop: bool = False,
            refresh_server_playback: bool = True,
            rfile: Optional[str] = None,
            scripts: Sequence[str] = [],
            showhost: bool = False,
            replacements: Sequence[Tuple[str, str, str]] = [],
            server_replay_use_headers: Sequence[str] = [],
            setheaders: Sequence[Tuple[str, str, str]] = [],
            server_replay: Sequence[str] = [],
            stickycookie: Optional[str] = None,
            stickyauth: Optional[str] = None,
            stream_large_bodies: Optional[int] = None,
            verbosity: int = 2,
            default_contentview: str = "auto",
            streamfile: Optional[str] = None,
            streamfile_append: bool = False,
            server_replay_ignore_content: bool = False,
            server_replay_ignore_params: Sequence[str] = [],
            server_replay_ignore_payload_params: Sequence[str] = [],
            server_replay_ignore_host: bool = False,
            # Proxy options
            auth_nonanonymous: bool = False,
            auth_singleuser: Optional[str] = None,
            auth_htpasswd: Optional[str] = None,
            add_upstream_certs_to_client_chain: bool = False,
            body_size_limit: Optional[int] = None,
            cadir: str = CA_DIR,
            certs: Sequence[Tuple[str, str]] = [],
            ciphers_client: str=DEFAULT_CLIENT_CIPHERS,
            ciphers_server: Optional[str]=None,
            clientcerts: Optional[str] = None,
            http2: bool = True,
            ignore_hosts: Sequence[str] = [],
            listen_host: str = "",
            listen_port: int = LISTEN_PORT,
            upstream_bind_address: str = "",
            mode: str = "regular",
            no_upstream_cert: bool = False,
            rawtcp: bool = False,
            websocket: bool = True,
            spoof_source_address: bool = False,
            upstream_server: Optional[str] = None,
            upstream_auth: Optional[str] = None,
            ssl_version_client: str = "secure",
            ssl_version_server: str = "secure",
            ssl_insecure: bool = False,
            ssl_verify_upstream_trusted_cadir: Optional[str] = None,
            ssl_verify_upstream_trusted_ca: Optional[str] = None,
            tcp_hosts: Sequence[str] = [],

            intercept: Optional[str] = None,

            # Console options
            eventlog: bool = False,
            focus_follow: bool = False,
            filter: Optional[str] = None,
            palette: Optional[str] = "dark",
            palette_transparent: bool = False,
            no_mouse: bool = False,
            order: Optional[str] = None,
            order_reversed: bool = False,

            # Web options
            open_browser: bool = True,
            wdebug: bool = False,
            wport: int = 8081,
            wiface: str = "127.0.0.1",

            # Dump options
            filtstr: Optional[str] = None,
            flow_detail: int = 1
    ) -> None:
        # We could replace all assignments with clever metaprogramming,
        # but type hints are a much more valueable asset.

        self.app = app
        self.app_host = app_host
        self.app_port = app_port
        self.anticache = anticache
        self.anticomp = anticomp
        self.client_replay = client_replay
        self.keepserving = keepserving
        self.replay_kill_extra = replay_kill_extra
        self.no_server = no_server
        self.server_replay_nopop = server_replay_nopop
        self.refresh_server_playback = refresh_server_playback
        self.rfile = rfile
        self.scripts = scripts
        self.showhost = showhost
        self.replacements = replacements
        self.server_replay_use_headers = server_replay_use_headers
        self.setheaders = setheaders
        self.server_replay = server_replay
        self.stickycookie = stickycookie
        self.stickyauth = stickyauth
        self.stream_large_bodies = stream_large_bodies
        self.verbosity = verbosity
        self.default_contentview = default_contentview
        self.streamfile = streamfile
        self.streamfile_append = streamfile_append
        self.server_replay_ignore_content = server_replay_ignore_content
        self.server_replay_ignore_params = server_replay_ignore_params
        self.server_replay_ignore_payload_params = server_replay_ignore_payload_params
        self.server_replay_ignore_host = server_replay_ignore_host

        # Proxy options
        self.auth_nonanonymous = auth_nonanonymous
        self.auth_singleuser = auth_singleuser
        self.auth_htpasswd = auth_htpasswd
        self.add_upstream_certs_to_client_chain = add_upstream_certs_to_client_chain
        self.body_size_limit = body_size_limit
        self.cadir = cadir
        self.certs = certs
        self.ciphers_client = ciphers_client
        self.ciphers_server = ciphers_server
        self.clientcerts = clientcerts
        self.http2 = http2
        self.ignore_hosts = ignore_hosts
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.upstream_bind_address = upstream_bind_address
        self.mode = mode
        self.no_upstream_cert = no_upstream_cert
        self.rawtcp = rawtcp
        self.websocket = websocket
        self.spoof_source_address = spoof_source_address
        self.upstream_server = upstream_server
        self.upstream_auth = upstream_auth
        self.ssl_version_client = ssl_version_client
        self.ssl_version_server = ssl_version_server
        self.ssl_insecure = ssl_insecure
        self.ssl_verify_upstream_trusted_cadir = ssl_verify_upstream_trusted_cadir
        self.ssl_verify_upstream_trusted_ca = ssl_verify_upstream_trusted_ca
        self.tcp_hosts = tcp_hosts

        self.intercept = intercept

        # Console options
        self.eventlog = eventlog
        self.focus_follow = focus_follow
        self.filter = filter
        self.palette = palette
        self.palette_transparent = palette_transparent
        self.no_mouse = no_mouse
        self.order = order
        self.order_reversed = order_reversed

        # Web options
        self.open_browser = open_browser
        self.wdebug = wdebug
        self.wport = wport
        self.wiface = wiface

        # Dump options
        self.filtstr = filtstr
        self.flow_detail = flow_detail

        super().__init__()
