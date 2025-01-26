# This is a copy of dump.py that is set to load the browserup proxy add-ons
# Keep an eye on dump.py for updates to incorporate

from mitmproxy import addons
from mitmproxy import master
from mitmproxy import options
from mitmproxy.addons import dumper
from mitmproxy.addons import keepserving
from mitmproxy.addons import readfile
from mitmproxy.addons import termlog
from mitmproxy.addons.browserup import browser_data_addon
from mitmproxy.addons.browserup import browserup_addons_manager
from mitmproxy.addons.browserup import har_capture_addon
from mitmproxy.addons.browserup import latency_addon
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

        harCaptureAddon = har_capture_addon.HarCaptureAddOn()
        self.addons.add(
            browserup_addons_manager.BrowserUpAddonsManagerAddOn(),
            harCaptureAddon,
            browser_data_addon.BrowserDataAddOn(harCaptureAddon),
            latency_addon.LatencyAddOn(),
        )
        self.addons.add(
            keepserving.KeepServing(), readfile.ReadFileStdin(), self.errorcheck
        )
