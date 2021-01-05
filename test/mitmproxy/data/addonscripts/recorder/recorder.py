from mitmproxy import ctx
from mitmproxy import hooks


class Recorder:
    call_log = []

    def __init__(self, name="recorder"):
        self.name = name

    def __getattr__(self, attr):
        if attr in hooks.all_hooks:
            def prox(*args, **kwargs):
                lg = (self.name, attr, args, kwargs)
                if attr != "add_log":
                    ctx.log.info(str(lg))
                    self.call_log.append(lg)
                    ctx.log.debug(f"{self.name} {attr}")

            return prox
        raise AttributeError


addons = [Recorder()]
