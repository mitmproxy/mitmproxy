from mitmproxy import controller
from mitmproxy import eventsequence
from mitmproxy import ctx


class Recorder:
    call_log = []

    def __init__(self, name = "recorder"):
        self.name = name

    def __getattr__(self, attr):
        if attr in eventsequence.Events:
            def prox(*args, **kwargs):
                lg = (self.name, attr, args, kwargs)
                if attr != "log":
                    ctx.log.info(str(lg))
                    self.call_log.append(lg)
                    ctx.log.debug("%s %s" % (self.name, attr))
            return prox
        raise AttributeError


addons = [Recorder()]
