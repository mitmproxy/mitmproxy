# This is a copy of dump.py that is set to load the browserup proxy add-ons
# Keep an eye on dump.py for updates to incorporate

from mitmproxy import addons
from mitmproxy import options
from mitmproxy import master
from mitmproxy.addons import dumper, termlog, keepserving, readfile
from mitmproxy.addons.browserup import har_dump, init_flow, http_connect_capture, browserup_addons_manager, allow_list, block_list


class ErrorCheck:
    def __init__(self):
        self.has_errored = False

    def add_log(self, e):
        if e.level == "error":
            self.has_errored = True


class DumpMaster(master.Master):

    def __init__(
        self,
        options: options.Options,
        with_termlog=True,
        with_dumper=True,
    ) -> None:
        super().__init__(options)
        self.errorcheck = ErrorCheck()
        if with_termlog:
            self.addons.add(termlog.TermLog())
        self.addons.add(*addons.default_addons())

        self.addons.add(dumper.Dumper())

        self.addons.add(http_connect_capture.HttpConnectCaptureAddOn())
        self.addons.add(har_dump.HarDumpAddOn())

        self.addons.add(
            keepserving.KeepServing(),
            readfile.ReadFileStdin(),
            init_flow.BrowserupInitFlowAddOn(),
            browserup_addons_manager.BrowserUpAddonsManagerAddOn(),
            allow_list.AllowListAddOn(),
            block_list.BlockListAddOn(),
            self.errorcheck
        )


