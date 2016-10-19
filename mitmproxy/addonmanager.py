from mitmproxy import exceptions
import pprint


def _get_name(itm):
    return getattr(itm, "name", itm.__class__.__name__.lower())


class AddonManager:
    def __init__(self, master):
        self.chain = []
        self.master = master
        master.options.changed.connect(self._options_update)

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

    def _options_update(self, options, updated):
        for i in self.chain:
            with self.master.handlecontext():
                self.invoke_with_context(i, "configure", options, updated)

    def startup(self, s):
        """
            Run startup events on addon.
        """
        self.invoke_with_context(s, "start")
        self.invoke_with_context(
            s,
            "configure",
            self.master.options,
            self.master.options.keys()
        )

    def add(self, *addons):
        """
            Add addons to the end of the chain, and run their startup events.
        """
        self.chain.extend(addons)
        for i in addons:
            self.startup(i)

    def remove(self, addon):
        """
            Remove an addon from the chain, and run its done events.
        """
        self.chain = [i for i in self.chain if i is not addon]
        self.invoke_with_context(addon, "done")

    def done(self):
        for i in self.chain:
            self.invoke_with_context(i, "done")

    def __len__(self):
        return len(self.chain)

    def __str__(self):
        return pprint.pformat([str(i) for i in self.chain])

    def invoke_with_context(self, addon, name, *args, **kwargs):
        with self.master.handlecontext():
            self.invoke(addon, name, *args, **kwargs)

    def invoke(self, addon, name, *args, **kwargs):
        func = getattr(addon, name, None)
        if func:
            if not callable(func):
                raise exceptions.AddonError(
                    "Addon handler %s not callable" % name
                )
            func(*args, **kwargs)

    def __call__(self, name, *args, **kwargs):
        for i in self.chain:
            try:
                self.invoke(i, name, *args, **kwargs)
            except exceptions.AddonHalt:
                return
