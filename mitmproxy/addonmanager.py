import typing

from mitmproxy import exceptions
from mitmproxy import eventsequence
from mitmproxy import controller
from . import ctx
import pprint


def _get_name(itm):
    return getattr(itm, "name", itm.__class__.__name__.lower())


class Loader:
    """
        A loader object is passed to the load() event when addons start up.
    """
    def __init__(self, master):
        self.master = master
        self.boot_into_addon = None

    def add_option(
        self,
        name: str,
        typespec: type,
        default: typing.Any,
        help: str,
        choices: typing.Optional[typing.Sequence[str]] = None
    ) -> None:
        self.master.options.add_option(
            name,
            typespec,
            default,
            help,
            choices
        )

    def boot_into(self, addon):
        self.boot_into_addon = addon
        func = getattr(addon, "load", None)
        if func:
            func(self)


class AddonManager:
    def __init__(self, master):
        self.lookup = {}
        self.chain = []
        self.master = master
        master.options.changed.connect(self._configure_all)

    def _configure_all(self, options, updated):
        self.trigger("configure", options, updated)

    def clear(self):
        """
            Remove all addons.
        """
        for i in self.chain:
            self.remove(i)

    def get(self, name):
        """
            Retrieve an addon by name. Addon names are equal to the .name
            attribute on the instance, or the lower case class name if that
            does not exist.
        """
        return self.lookup.get(name, None)

    def register(self, addon):
        """
            Register an addon with the manager without adding it to the chain.
            This should be used by addons that manage addons. Must be called
            within a current context.
        """
        l = Loader(self.master)
        self.invoke_addon(addon, "load", l)
        if l.boot_into_addon:
            addon = l.boot_into_addon
        name = _get_name(addon)
        if name in self.lookup:
            raise exceptions.AddonError(
                "An addon called '%s' already exists." % name
            )
        self.lookup[name] = addon
        return addon

    def add(self, *addons):
        """
            Add addons to the end of the chain, and run their load event.
        """
        with self.master.handlecontext():
            for i in addons:
                self.chain.append(self.register(i))

    def remove(self, addon):
        """
            Remove an addon from the chain, and run its done events.
        """
        n = _get_name(addon)
        if n not in self.lookup:
            raise exceptions.AddonError("No such addon: %s" % n)
        self.chain = [i for i in self.chain if i is not addon]
        del self.lookup[_get_name(addon)]
        with self.master.handlecontext():
            self.invoke_addon(addon, "done")

    def __len__(self):
        return len(self.chain)

    def __str__(self):
        return pprint.pformat([str(i) for i in self.chain])

    def handle_lifecycle(self, name, message):
        """
            Handle a lifecycle event.
        """
        if not hasattr(message, "reply"):  # pragma: no cover
            raise exceptions.ControlException(
                "Message %s has no reply attribute" % message
            )

        # We can use DummyReply objects multiple times. We only clear them up on
        # the next handler so that we can access value and state in the
        # meantime.
        if isinstance(message.reply, controller.DummyReply):
            message.reply.reset()

        self.trigger(name, message)

        if message.reply.state != "taken":
            message.reply.take()
            if not message.reply.has_message:
                message.reply.ack()
            message.reply.commit()

            if isinstance(message.reply, controller.DummyReply):
                message.reply.mark_reset()

    def invoke_addon(self, addon, name, *args, **kwargs):
        """
            Invoke an event on an addon. This method must run within an
            established handler context.
        """
        if not ctx.master:
            raise exceptions.AddonError(
                "invoke_addon called without a handler context."
            )
        if name not in eventsequence.Events:
            name = "event_" + name
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
