from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import addons
from mitmproxy import options
from mitmproxy import master
from mitmproxy.addons import dumper, termlog, termstatus


class DumpMaster(master.Master):

    def __init__(
            self,
            options: options.Options,
            server,
            with_termlog=True,
            with_dumper=True,
    ) -> None:
        master.Master.__init__(self, options, server)
        self.has_errored = False
        if with_termlog:
            self.addons.add(termlog.TermLog(), termstatus.TermStatus())
        self.addons.add(*addons.default_addons())
        if with_dumper:
            self.addons.add(dumper.Dumper())

        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except exceptions.FlowReadException as v:
                self.add_log("Flow file corrupted.", "error")
                raise exceptions.OptionsError(v)

    @controller.handler
    def log(self, e):
        if e.level == "error":
            self.has_errored = True

    def run(self):  # pragma: no cover
        if self.options.rfile and not self.options.keepserving:
            self.addons.done()
            return
        super().run()
