from __future__ import absolute_import, print_function, division
from mitmproxy import options
from typing import Tuple, Optional, Sequence  # noqa

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
        super(Options, self).__init__()
