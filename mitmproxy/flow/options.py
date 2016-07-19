from __future__ import absolute_import, print_function, division
from mitmproxy import options
from typing import Tuple, Optional, Sequence  # noqa
from mitmproxy import cmdline

APP_HOST = "mitm.it"
APP_PORT = 80


class Options(options.Options):
    def __init__(
            self,
            # TODO: rename to onboarding_app_*
            app=True,  # type: bool
            app_host=APP_HOST,  # type: str
            app_port=APP_PORT,  # type: int
            anticache=False,  # type: bool
            anticomp=False,  # type: bool
            client_replay=None,  # type: Optional[str]
            kill=False,  # type: bool
            no_server=False,  # type: bool
            nopop=False,  # type: bool
            refresh_server_playback=False,  # type: bool
            rfile=None,  # type: Optional[str]
            scripts=(),  # type: Sequence[str]
            showhost=False,  # type: bool
            replacements=(),  # type: Sequence[Tuple[str, str, str]]
            rheaders=(),  # type: Sequence[str]
            setheaders=(),  # type: Sequence[Tuple[str, str, str]]
            server_replay=None,  # type: Optional[str]
            stickycookie=None,  # type: Optional[str]
            stickyauth=None,  # type: Optional[str]
            stream_large_bodies=None,  # type: Optional[str]
            verbosity=2,  # type: int
            outfile=None,  # type: Tuple[str, str]
            replay_ignore_content=False,  # type: bool
            replay_ignore_params=(),  # type: Sequence[str]
            replay_ignore_payload_params=(),  # type: Sequence[str]
            replay_ignore_host=False,  # type: bool

            # Proxy options
            auth_nonanonymous=False,  # type: bool
            auth_singleuser=None,  # type: Optional[str]
            auth_htpasswd=None,  # type: Optional[str]
            add_upstream_certs_to_client_chain=False,  # type: bool
            body_size_limit=None,  # type: Optional[int]
            cadir = cmdline.CA_DIR,  # type: str
            certs = (),  # type: Sequence[Tuple[str, str]]
            ciphers_client = cmdline.DEFAULT_CLIENT_CIPHERS,   # type: str
            ciphers_server = None,   # type: Optional[str]
            clientcerts = None,  # type: Optional[str]
            http2 = True,  # type: bool
            ignore_hosts = (),  # type: Sequence[str]
            listen_host = "",  # type: str
            listen_port = 8080,  # type: int
            mode = "regular",  # type: str
            no_upstream_cert = False,  # type: bool
            rawtcp = False,  # type: bool
            upstream_server = "",  # type: str
            upstream_auth = "",  # type: str
            ssl_version_client="secure",  # type: str
            ssl_version_server="secure",  # type: str
            ssl_verify_upstream_cert=False,  # type: bool
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
        self.kill = kill
        self.no_server = no_server
        self.nopop = nopop
        self.refresh_server_playback = refresh_server_playback
        self.rfile = rfile
        self.scripts = scripts
        self.showhost = showhost
        self.replacements = replacements
        self.rheaders = rheaders
        self.setheaders = setheaders
        self.server_replay = server_replay
        self.stickycookie = stickycookie
        self.stickyauth = stickyauth
        self.stream_large_bodies = stream_large_bodies
        self.verbosity = verbosity
        self.outfile = outfile
        self.replay_ignore_content = replay_ignore_content
        self.replay_ignore_params = replay_ignore_params
        self.replay_ignore_payload_params = replay_ignore_payload_params
        self.replay_ignore_host = replay_ignore_host

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
        self.ssl_verify_upstream_cert = ssl_verify_upstream_cert
        self.ssl_verify_upstream_trusted_cadir = ssl_verify_upstream_trusted_cadir
        self.ssl_verify_upstream_trusted_ca = ssl_verify_upstream_trusted_ca
        self.tcp_hosts = tcp_hosts
        super(Options, self).__init__()
