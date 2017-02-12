from typing import Optional

from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import addons
from mitmproxy import options
from mitmproxy import master
from mitmproxy.addons import dumper, termlog


class DumpError(Exception):
    pass


class Options(options.Options):
    def __init__(
            self,
            *,  # all args are keyword-only.
            keepserving: bool = False,
            filtstr: Optional[str] = None,
            flow_detail: int = 1,
            **kwargs
    ) -> None:
        self.filtstr = filtstr
        self.flow_detail = flow_detail
        self.keepserving = keepserving
        super().__init__(**kwargs)


class DumpMaster(master.Master):

    def __init__(
            self,
            options: Options,
            server,
            with_termlog=True,
            with_dumper=True,
    ) -> None:
        master.Master.__init__(self, options, server)
        self.has_errored = False
        if with_termlog:
            self.addons.add(termlog.TermLog())
        self.addons.add(*addons.default_addons())
        if with_dumper:
            self.addons.add(dumper.Dumper())

        if not self.options.no_server:
            self.add_log(
                "Proxy server listening at http://{}".format(server.address),
                "info"
            )

        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except exceptions.FlowReadException as v:
                self.add_log("Flow file corrupted.", "error")
                raise DumpError(v)

    @controller.handler
    def log(self, e):
        if e.level == "error":
            self.has_errored = True

    def run(self):  # pragma: no cover
        if self.options.rfile and not self.options.keepserving:
            self.addons.done()
            return
        super().run()
