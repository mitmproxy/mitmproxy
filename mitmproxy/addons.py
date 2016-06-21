from __future__ import absolute_import, print_function, division
from mitmproxy import exceptions
import pprint


def _get_name(itm):
    return getattr(itm, "name", itm.__class__.__name__)


class Addons(object):
    def __init__(self, master):
        self.chain = []
        self.master = master
        master.options.changed.connect(self.options_update)

    def options_update(self, options):
        for i in self.chain:
            with self.master.handlecontext(None):
                i.configure(options)

    def add(self, *addons):
        self.chain.extend(addons)
        for i in addons:
            self.invoke_with_context(i, "configure", self.master.options)

    def remove(self, addon):
        self.chain = [i for i in self.chain if i is not addon]
        self.invoke_with_context(addon, "done")

    def done(self):
        for i in self.chain:
            self.invoke_with_context(i, "done")

    def has_addon(self, name):
        """
            Is an addon with this name registered?
        """
        for i in self.chain:
            if _get_name(i) == name:
                return True

    def __len__(self):
        return len(self.chain)

    def __str__(self):
        return pprint.pformat([str(i) for i in self.chain])

    def invoke_with_context(self, addon, name, *args, **kwargs):
        with self.master.handlecontext(None):
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
            self.invoke(i, name, *args, **kwargs)
