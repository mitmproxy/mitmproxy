import typing
from typing import Optional

from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import addons
from mitmproxy import io
from mitmproxy import options
from mitmproxy import master
from mitmproxy.addons import dumper, termlog
from mitmproxy.net import tcp


class DumpError(Exception):
    pass


class Options(options.Options):
    def __init__(
            self,
            keepserving: bool = False,
            filtstr: Optional[str] = None,
            flow_detail: int = 1,
            tfile: Optional[typing.io.TextIO] = None,
            **kwargs
    ):
        self.filtstr = filtstr
        self.flow_detail = flow_detail
        self.keepserving = keepserving
        self.tfile = tfile
        super().__init__(**kwargs)


class DumpMaster(master.Master):

    def __init__(self, options, server):
        master.Master.__init__(self, options, server)
        self.has_errored = False
        self.addons.add(termlog.TermLog())
        self.addons.add(*addons.default_addons())
        self.addons.add(dumper.Dumper())
        # This line is just for type hinting
        self.options = self.options  # type: Options

        if not self.options.no_server:
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

    def _readflow(self, paths):
        """
        Utitility function that reads a list of flows
        or raises a DumpError if that fails.
        """
        try:
            return io.read_flows_from_paths(paths)
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
        super().run()
