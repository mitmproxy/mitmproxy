import contextlib

import mitmproxy.master
import mitmproxy.options
from mitmproxy import proxy
from mitmproxy import events
from mitmproxy import exceptions


class RecordingMaster(mitmproxy.master.Master):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_log = []

    def add_log(self, e, level):
        self.event_log.append((level, e))

    def clear(self):
        self.event_log = []


class context:
    """
        A context for testing addons, which sets up the mitmproxy.ctx module so
        handlers can run as they would within mitmproxy. The context also
        provides a number of helper methods for common testing scenarios.
    """
    def __init__(self, master = None, options = None):
        self.options = options or mitmproxy.options.Options()
        self.master = master or RecordingMaster(
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

    @contextlib.contextmanager
    def _rollback(self, opts, updates):
        old = opts._opts.copy()
        try:
            yield
        except exceptions.OptionsError as e:
            opts.__dict__["_opts"] = old
            raise

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
        with self._rollback(self.options, kwargs):
            self.options.update(**kwargs)
            addon.configure(self.options, kwargs.keys())
