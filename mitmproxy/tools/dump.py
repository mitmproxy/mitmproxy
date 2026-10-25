from mitmproxy import addons
from mitmproxy import master
from mitmproxy import options
from mitmproxy.addons import dumper
from mitmproxy.addons import errorcheck
from mitmproxy.addons import keepserving
from mitmproxy.addons import readfile
from mitmproxy.addons import websocket_history


class DumpMaster(master.Master):
    def __init__(
        self,
        options: options.Options,
        loop=None,
        with_termlog=True,
        with_dumper=True,
    ) -> None:
        super().__init__(options, event_loop=loop, with_termlog=with_termlog)
        # Run before scripts (which may request history) and capture addons
        # (which must not open a file before we reject an unsafe option change).
        self.addons.add(websocket_history.WebSocketHistory())
        self.addons.add(*addons.default_addons())
        if with_dumper:
            self.addons.add(dumper.Dumper())
        self.addons.add(
            keepserving.KeepServing(),
            readfile.ReadFileStdin(),
            errorcheck.ErrorCheck(),
        )
