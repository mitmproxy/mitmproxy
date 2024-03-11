import logging

from mitmproxy import hooks


class Recorder:
    call_log = []

    def __init__(self, name="recorder"):
        self.name = name

    def __getattr__(self, attr):
        if attr in hooks.all_hooks and attr != "add_log":

            def prox(*args, **kwargs):
                lg = (self.name, attr, args, kwargs)
                logging.info(str(lg))
                self.call_log.append(lg)
                logging.debug(f"{self.name} {attr}")

            return prox
        raise AttributeError


addons = [Recorder()]
