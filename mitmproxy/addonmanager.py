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
            l = Loader(self.master)
            for i in addons:
                self.invoke_addon(i, "load", l)

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
