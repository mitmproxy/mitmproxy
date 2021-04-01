# This is a copy of dump.py that is set to load the browserup proxy add-ons
# Keep an eye on dump.py for updates to incorporate

from mitmproxy import addons
from mitmproxy import options
from mitmproxy import master
from mitmproxy.addons import dumper, termlog, keepserving, readfile
from mitmproxy.addons.browserup import har_capture, init_flow, http_connect_capture, \
    browserup_addons_manager, allow_list, block_list, auth_basic, proxy_manager, latency, additional_headers


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
        self.addons.add(har_capture.HarCaptureAddOn())

        self.addons.add(
            keepserving.KeepServing(),
            readfile.ReadFileStdin(),
            init_flow.BrowserupInitFlowAddOn(),
            browserup_addons_manager.BrowserUpAddonsManagerAddOn(),
            auth_basic.AuthBasicAddOn(),
            allow_list.AllowListAddOn(),
            block_list.BlockListAddOn(),
            additional_headers.AddHeadersAddOn(),
            latency.LatencyAddOn(),
            proxy_manager.ProxyManagerAddOn(),
            self.errorcheck
        )


