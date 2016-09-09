from __future__ import absolute_import, print_function, division

import sys

from typing import Optional  # noqa
import typing  # noqa

import click

from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import builtins
from mitmproxy import utils
from mitmproxy import options
from mitmproxy.builtins import dumper
from netlib import tcp


class DumpError(Exception):
    pass


class Options(options.Options):
    def __init__(
            self,
            keepserving=False,  # type: bool
            filtstr=None,  # type: Optional[str]
            flow_detail=1,  # type: int
            tfile=None,  # type: Optional[typing.io.TextIO]
            **kwargs
    ):
        self.filtstr = filtstr
        self.flow_detail = flow_detail
        self.keepserving = keepserving
        self.tfile = tfile
        super(Options, self).__init__(**kwargs)


class DumpMaster(flow.FlowMaster):

    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, options, server, flow.State())
        self.has_errored = False
        self.addons.add(options, *builtins.default_addons())
        self.addons.add(options, dumper.Dumper())
        # This line is just for type hinting
        self.options = self.options  # type: Options
        self.server_replay_ignore_params = options.server_replay_ignore_params
        self.server_replay_ignore_content = options.server_replay_ignore_content
        self.server_replay_ignore_host = options.server_replay_ignore_host
        self.refresh_server_playback = options.refresh_server_playback
        self.server_replay_ignore_payload_params = options.server_replay_ignore_payload_params

        self.set_stream_large_bodies(options.stream_large_bodies)

        if self.server and self.options.http2 and not tcp.HAS_ALPN:  # pragma: no cover
            print("ALPN support missing (OpenSSL 1.0.2+ required)!\n"
                  "HTTP/2 is disabled. Use --no-http2 to silence this warning.",
                  file=sys.stderr)

        if options.client_replay:
            self.start_client_playback(
                self._readflow(options.client_replay),
                not options.keepserving
            )

        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except exceptions.FlowReadException as v:
                self.add_log("Flow file corrupted.", "error")
                raise DumpError(v)

        if self.options.app:
            self.start_app(self.options.app_host, self.options.app_port)

    def _readflow(self, paths):
        """
        Utitility function that reads a list of flows
        or raises a DumpError if that fails.
        """
        try:
            return flow.read_flows_from_paths(paths)
        except exceptions.FlowReadException as e:
            raise DumpError(str(e))

    def add_log(self, e, level="info"):
        if level == "error":
            self.has_errored = True
        if self.options.verbosity >= utils.log_tier(level):
            click.secho(
                e,
                file=self.options.tfile,
                fg=dict(error="red", warn="yellow").get(level),
                dim=(level == "debug"),
                err=(level == "error")
            )

    @controller.handler
    def request(self, f):
        f = super(DumpMaster, self).request(f)
        if f:
            self.state.delete_flow(f)
        return f

    def run(self):  # pragma: no cover
        if self.options.rfile and not self.options.keepserving:
            self.addons.done()
            return
        super(DumpMaster, self).run()
