import typing
import traceback
import contextlib
import sys

from mitmproxy import exceptions
from mitmproxy import eventsequence
from mitmproxy import controller
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


class StreamLog:
    """
        A class for redirecting output using contextlib.
    """
    def __init__(self, log):
        self.log = log

    def write(self, buf):
        if buf.strip():
            self.log(buf)

    def flush(self):  # pragma: no cover
        # Click uses flush sometimes, so we dummy it up
        pass


@contextlib.contextmanager
def safecall():
    stdout_replacement = StreamLog(ctx.log.warn)
    try:
        with contextlib.redirect_stdout(stdout_replacement):
            yield
    except exceptions.AddonHalt:
        raise
    except Exception as e:
        etype, value, tb = sys.exc_info()
        tb = cut_traceback(tb, "invoke_addon").tb_next
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
        if name in self.master.options:
            ctx.log.warn("Over-riding existing option %s" % name)
        self.master.options.add_option(
            name,
            typespec,
            default,
            help,
            choices
        )

    def add_command(self, path: str, func: typing.Callable) -> None:
        self.master.commands.add_command(path, func)


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
                raise exceptions.AddonError(
                    "An addon called '%s' already exists." % name
                )
        l = Loader(self.master)
        self.invoke_addon(addon, "load", l)
        for a in traverse([addon]):
            name = _get_name(a)
            self.lookup[name] = a
        return addon

    def add(self, *addons):
        """
            Add addons to the end of the chain, and run their load event.
            If any addon has sub-addons, they are registered.
        """
        with self.master.handlecontext():
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
                raise exceptions.AddonError("No such addon: %s" % n)
            self.chain = [i for i in self.chain if i is not a]
            del self.lookup[_get_name(a)]
        with self.master.handlecontext():
            self.invoke_addon(a, "done")

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
            Invoke an event on an addon and all its children. This method must
            run within an established handler context.
        """
        if name not in eventsequence.Events:
            name = "event_" + name
        for a in traverse([addon]):
            func = getattr(a, name, None)
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
                    with safecall():
                        self.invoke_addon(i, name, *args, **kwargs)
                except exceptions.AddonHalt:
                    return
