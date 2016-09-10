from __future__ import absolute_import, print_function, division
from mitmproxy import optmanager
from typing import Tuple, Optional, Sequence  # noqa

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
            # TODO: rename to onboarding_app_*
            app=True,  # type: bool
            app_host=APP_HOST,  # type: str
            app_port=APP_PORT,  # type: int
            anticache=False,  # type: bool
            anticomp=False,  # type: bool
            client_replay=None,  # type: Optional[str]
            replay_kill_extra=False,  # type: bool
            keepserving=True,  # type: bool
            no_server=False,  # type: bool
            server_replay_nopop=False,  # type: bool
            refresh_server_playback=False,  # type: bool
            rfile=None,  # type: Optional[str]
            scripts=(),  # type: Sequence[str]
            showhost=False,  # type: bool
            replacements=(),  # type: Sequence[Tuple[str, str, str]]
            server_replay_use_headers=(),  # type: Sequence[str]
            setheaders=(),  # type: Sequence[Tuple[str, str, str]]
            server_replay=None,  # type: Optional[str]
            stickycookie=None,  # type: Optional[str]
            stickyauth=None,  # type: Optional[str]
            stream_large_bodies=None,  # type: Optional[str]
            verbosity=2,  # type: int
            outfile=None,  # type: Tuple[str, str]
            server_replay_ignore_content=False,  # type: bool
            server_replay_ignore_params=(),  # type: Sequence[str]
            server_replay_ignore_payload_params=(),  # type: Sequence[str]
            server_replay_ignore_host=False,  # type: bool

            # Proxy options
            auth_nonanonymous=False,  # type: bool
            auth_singleuser=None,  # type: Optional[str]
            auth_htpasswd=None,  # type: Optional[str]
            add_upstream_certs_to_client_chain=False,  # type: bool
            body_size_limit=None,  # type: Optional[int]
            cadir = CA_DIR,  # type: str
            certs = (),  # type: Sequence[Tuple[str, str]]
            ciphers_client = DEFAULT_CLIENT_CIPHERS,   # type: str
            ciphers_server = None,   # type: Optional[str]
            clientcerts = None,  # type: Optional[str]
            http2 = True,  # type: bool
            ignore_hosts = (),  # type: Sequence[str]
            listen_host = "",  # type: str
            listen_port = LISTEN_PORT,  # type: int
            mode = "regular",  # type: str
            no_upstream_cert = False,  # type: bool
            rawtcp = False,  # type: bool
            upstream_server = "",  # type: str
            upstream_auth = "",  # type: str
            ssl_version_client="secure",  # type: str
            ssl_version_server="secure",  # type: str
            ssl_insecure=False,  # type: bool
            ssl_verify_upstream_trusted_cadir=None,  # type: str
            ssl_verify_upstream_trusted_ca=None,  # type: str
            tcp_hosts = (),  # type: Sequence[str]
    ):
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
        self.outfile = outfile
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
        self.mode = mode
        self.no_upstream_cert = no_upstream_cert
        self.rawtcp = rawtcp
        self.upstream_server = upstream_server
        self.upstream_auth = upstream_auth
        self.ssl_version_client = ssl_version_client
        self.ssl_version_server = ssl_version_server
        self.ssl_insecure = ssl_insecure
        self.ssl_verify_upstream_trusted_cadir = ssl_verify_upstream_trusted_cadir
        self.ssl_verify_upstream_trusted_ca = ssl_verify_upstream_trusted_ca
        self.tcp_hosts = tcp_hosts
        super(Options, self).__init__()
