# This is a copy of dump.py that is set to load the browserup proxy add-ons
# Keep an eye on dump.py for updates to incorporate

from mitmproxy import addons
from mitmproxy import options
from mitmproxy import master

from mitmproxy.addons import dumper, termlog, keepserving, readfile
from mitmproxy.addons.browserup import har_capture_addon, \
    browserup_addons_manager, latency_addon, page_perf_script_addon

from mitmproxy.addons.errorcheck import ErrorCheck


class BrowserupProxyMaster(master.Master):

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

        self.addons.add(browserup_addons_manager.BrowserUpAddonsManagerAddOn(), page_perf_script_addon.PagePerfScriptAddOn(),
                        har_capture_addon.HarCaptureAddOn(), latency_addon.LatencyAddOn())
        self.addons.add(
            keepserving.KeepServing(),
            readfile.ReadFileStdin(),
            self.errorcheck
        )
