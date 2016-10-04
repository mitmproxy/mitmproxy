from mitmproxy import controller
from mitmproxy import ctx
import sys


class CallLogger:
    call_log = []

    def __init__(self, name = "solo"):
        self.name = name

    def __getattr__(self, attr):
        if attr in controller.Events:
            def prox(*args, **kwargs):
                lg = (self.name, attr, args, kwargs)
                if attr != "log":
                    ctx.log.info(str(lg))
                    self.call_log.append(lg)
                    ctx.log.debug("%s %s" % (self.name, attr))
            return prox
        raise AttributeError


def start():
    return CallLogger(*sys.argv[1:])
