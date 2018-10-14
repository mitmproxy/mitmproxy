import types
import typing
import traceback
import contextlib
import sys

from mitmproxy import exceptions
from mitmproxy import eventsequence
from mitmproxy import controller
from mitmproxy import flow
from . import ctx
import pprint


def _get_name(itm):
    return getattr(itm, "name", itm.__class__.__name__.lower())


def cut_traceback(tb, func_name):
    """
    Cut off a traceback at the function with the given name.
    The func_name's frame is excluded.

    Args:
        tb: traceback object, as returned by sys.exc_info()[2]
        func_name: function name

    Returns:
        Reduced traceback.
    """
    tb_orig = tb
    for _, _, fname, _ in traceback.extract_tb(tb):
        tb = tb.tb_next
        if fname == func_name:
            break
    return tb or tb_orig


@contextlib.contextmanager
def safecall():
    try:
        yield
    except (exceptions.AddonHalt, exceptions.OptionsError):
        raise
    except Exception as e:
        etype, value, tb = sys.exc_info()
        tb = cut_traceback(tb, "invoke_addon")
        ctx.log.error(
            "Addon error: %s" % "".join(
                traceback.format_exception(etype, value, tb)
            )
        )


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
        """
            Add an option to mitmproxy.

            Help should be a single paragraph with no linebreaks - it will be
            reflowed by tools. Information on the data type should be omitted -
            it will be generated and added by tools as needed.
        """
        if name in self.master.options:
            existing = self.master.options._options[name]
            same_signature = (
                existing.name == name and
                existing.typespec == typespec and
                existing.default == default and
                existing.help == help and
                existing.choices == choices
            )
            if same_signature:
                return
            else:
                ctx.log.warn("Over-riding existing option %s" % name)
        self.master.options.add_option(
            name,
            typespec,
            default,
            help,
            choices
        )

    def add_command(self, path: str, func: typing.Callable) -> None:
        self.master.commands.add(path, func)


def traverse(chain):
    """
        Recursively traverse an addon chain.
    """
    for a in chain:
        yield a
        if hasattr(a, "addons"):
            yield from traverse(a.addons)


class AddonManager:
    def __init__(self, master):
        self.lookup = {}
        self.chain = []
        self.master = master
        master.options.changed.connect(self._configure_all)

    def _configure_all(self, options, updated):
        self.trigger("configure", updated)

    def clear(self):
        """
            Remove all addons.
        """
        for a in self.chain:
            self.invoke_addon(a, "done")
        self.lookup = {}
        self.chain = []

    def get(self, name):
        """
            Retrieve an addon by name. Addon names are equal to the .name
            attribute on the instance, or the lower case class name if that
            does not exist.
        """
        return self.lookup.get(name, None)

    def register(self, addon):
        """
            Register an addon, call its load event, and then register all its
            sub-addons. This should be used by addons that dynamically manage
            addons.

            If the calling addon is already running, it should follow with
            running and configure events. Must be called within a current
            context.
        """
        for a in traverse([addon]):
            name = _get_name(a)
            if name in self.lookup:
                raise exceptions.AddonManagerError(
                    "An addon called '%s' already exists." % name
                )
        l = Loader(self.master)
        self.invoke_addon(addon, "load", l)
        for a in traverse([addon]):
            name = _get_name(a)
            self.lookup[name] = a
        for a in traverse([addon]):
            self.master.commands.collect_commands(a)
        self.master.options.process_deferred()
        return addon

    def add(self, *addons):
        """
            Add addons to the end of the chain, and run their load event.
            If any addon has sub-addons, they are registered.
        """
        for i in addons:
            self.chain.append(self.register(i))

    def remove(self, addon):
        """
            Remove an addon and all its sub-addons.

            If the addon is not in the chain - that is, if it's managed by a
            parent addon - it's the parent's responsibility to remove it from
            its own addons attribute.
        """
        for a in traverse([addon]):
            n = _get_name(a)
            if n not in self.lookup:
                raise exceptions.AddonManagerError("No such addon: %s" % n)
            self.chain = [i for i in self.chain if i is not a]
            del self.lookup[_get_name(a)]
        self.invoke_addon(a, "done")

    def __len__(self):
        return len(self.chain)

    def __str__(self):
        return pprint.pformat([str(i) for i in self.chain])

    def __contains__(self, item):
        name = _get_name(item)
        return name in self.lookup

    async def handle_lifecycle(self, name, message):
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

        if message.reply.state == "start":
            message.reply.take()
            if not message.reply.has_message:
                message.reply.ack()
            message.reply.commit()

            if isinstance(message.reply, controller.DummyReply):
                message.reply.mark_reset()

        if isinstance(message, flow.Flow):
            self.trigger("update", [message])

    def invoke_addon(self, addon, name, *args, **kwargs):
        """
            Invoke an event on an addon and all its children.
        """
        if name not in eventsequence.Events:
            raise exceptions.AddonManagerError("Unknown event: %s" % name)
        for a in traverse([addon]):
            func = getattr(a, name, None)
            if func:
                if callable(func):
                    func(*args, **kwargs)
                elif isinstance(func, types.ModuleType):
                    # we gracefully exclude module imports with the same name as hooks.
                    # For example, a user may have "from mitmproxy import log" in an addon,
                    # which has the same name as the "log" hook. In this particular case,
                    # we end up in an error loop because we "log" this error.
                    pass
                else:
                    raise exceptions.AddonManagerError(
                        "Addon handler {} ({}) not callable".format(name, a)
                    )

    def trigger(self, name, *args, **kwargs):
        """
            Trigger an event across all addons.
        """
        for i in self.chain:
            try:
                with safecall():
                    self.invoke_addon(i, name, *args, **kwargs)
            except exceptions.AddonHalt:
                return
