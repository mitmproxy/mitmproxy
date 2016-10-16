from __future__ import absolute_import, print_function, division

from typing import Optional  # noqa
import typing  # noqa

from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import builtins
from mitmproxy import options
from mitmproxy.builtins import dumper, termlog
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
        flow.FlowMaster.__init__(self, options, server, flow.DummyState())
        self.has_errored = False
        self.addons.add(termlog.TermLog())
        self.addons.add(*builtins.default_addons())
        self.addons.add(dumper.Dumper())
        # This line is just for type hinting
        self.options = self.options  # type: Options
        self.set_stream_large_bodies(options.stream_large_bodies)

        if not self.options.no_server and server:
            self.add_log(
                "Proxy server listening at http://{}".format(server.address),
                "info"
            )

        if self.server and self.options.http2 and not tcp.HAS_ALPN:  # pragma: no cover
            self.add_log(
                "ALPN support missing (OpenSSL 1.0.2+ required)!\n"
                "HTTP/2 is disabled. Use --no-http2 to silence this warning.",
                "error"
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

    @controller.handler
    def log(self, e):
        if e.level == "error":
            self.has_errored = True

    def run(self):  # pragma: no cover
        if self.options.rfile and not self.options.keepserving:
            self.addons.done()
            return
        super(DumpMaster, self).run()
