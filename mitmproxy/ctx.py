import mitmproxy.master  # noqa
import mitmproxy.log  # noqa
import mitmproxy.options  # noqa

master = None  # type: mitmproxy.master.Master
log: mitmproxy.log.Log = None
options: mitmproxy.options.Options = None
