from mitmproxy import exceptions
from mitmproxy import eventsequence
from . import ctx
import pprint


def _get_name(itm):
    return getattr(itm, "name", itm.__class__.__name__.lower())


class AddonManager:
    def __init__(self, master):
        self.chain = []
        self.master = master
        master.options.changed.connect(self.configure_all)

    def clear(self):
        """
            Remove all addons.
        """
        self.done()
        self.chain = []

    def get(self, name):
        """
            Retrieve an addon by name. Addon names are equal to the .name
            attribute on the instance, or the lower case class name if that
            does not exist.
        """
        for i in self.chain:
            if name == _get_name(i):
                return i

    def configure_all(self, options, updated):
        self.trigger("configure", options, updated)

    def add(self, *addons):
        """
            Add addons to the end of the chain, and run their startup events.
        """
        self.chain.extend(addons)
        with self.master.handlecontext():
            for i in addons:
                self.invoke_addon(i, "start", self.master.options)

    def remove(self, addon):
        """
            Remove an addon from the chain, and run its done events.
        """
        self.chain = [i for i in self.chain if i is not addon]
        with self.master.handlecontext():
            self.invoke_addon(addon, "done")

    def done(self):
        self.trigger("done")

    def __len__(self):
        return len(self.chain)

    def __str__(self):
        return pprint.pformat([str(i) for i in self.chain])

    def invoke_addon(self, addon, name, *args, **kwargs):
        """
            Invoke an event on an addon. This method must run within an
            established handler context.
        """
        if not ctx.master:
            raise exceptions.AddonError(
                "invoke_addon called without a handler context."
            )
        if name not in eventsequence.Events:  # prama: no cover
            raise NotImplementedError("Unknown event")
        func = getattr(addon, name, None)
        if func:
            if not callable(func):
                raise exceptions.AddonError(
                    "Addon handler %s not callable" % name
                )
            func(*args, **kwargs)

    def trigger(self, name, *args, **kwargs):
        """
            Establish a handler context and trigger an event across all addons
        """
        with self.master.handlecontext():
            for i in self.chain:
                try:
                    self.invoke_addon(i, name, *args, **kwargs)
                except exceptions.AddonHalt:
                    return

