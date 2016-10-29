import mitmproxy.master
import mitmproxy.options
from mitmproxy import proxy
from mitmproxy import events


class context:
    """
        A helper context for testing addons. Its most important function is to
        set up the ctx module so handlers can be called just like they would be
        when running from within mitmproxy.
    """
    def __init__(self, master = None, options = None):
        self.options = options or mitmproxy.options.Options()
        self.master = master or mitmproxy.master.Master(
            options, proxy.DummyServer(options)
        )
        self.wrapped = None

    def __enter__(self):
        self.wrapped = self.master.handlecontext()
        self.wrapped.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.wrapped.__exit__(exc_type, exc_value, traceback)
        self.wrapped = None
        return False

    def cycle(self, addon, f):
        """
            Cycles the flow through the events for the flow. Stops if a reply
            is taken (as in flow interception).
        """
        f.reply._state = "handled"
        for evt, arg in events.event_sequence(f):
            h = getattr(addon, evt, None)
            if h:
                h(arg)
                if f.reply.state == "taken":
                    return

    def configure(self, addon, **kwargs):
        """
            A helper for testing configure methods. Modifies the registered
            Options object with the given keyword arguments, then calls the
            configure method on the addon with the updated value.
        """
        for k, v in kwargs.items():
            setattr(self.options, k, v)
        addon.configure(self.options, kwargs.keys())
