from mitmproxy import addons
from mitmproxy import master
from mitmproxy import options
from mitmproxy.addons import dumper, errorcheck, keepserving, readfile, termlog


class DumpMaster(master.Master):
    def __init__(
        self,
        options: options.Options,
        with_termlog=True,
        with_dumper=True,
    ) -> None:
        super().__init__(options)
        if with_termlog:
            self.addons.add(termlog.TermLog())
        self.addons.add(*addons.default_addons())
        if with_dumper:
            self.addons.add(dumper.Dumper())
        self.addons.add(
            keepserving.KeepServing(),
            readfile.ReadFileStdin(),
            errorcheck.ErrorCheck(),
        )
