import contextlib
import inspect
import logging
import pprint
import sys
import traceback
import types
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import hooks

logger = logging.getLogger(__name__)


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
    except Exception:
        etype, value, tb = sys.exc_info()
        tb = cut_traceback(tb, "invoke_addon_sync")
        tb = cut_traceback(tb, "invoke_addon")
        assert etype
        assert value
        logger.error(
            f"Addon error: {value}",
            exc_info=(etype, value, tb),
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
        default: Any,
        help: str,
        choices: Sequence[str] | None = None,
    ) -> None:
        """
        Add an option to mitmproxy.

        Help should be a single paragraph with no linebreaks - it will be
        reflowed by tools. Information on the data type should be omitted -
        it will be generated and added by tools as needed.
        """
        assert not isinstance(choices, str)
        if name in self.master.options:
            existing = self.master.options._options[name]
            same_signature = (
                existing.name == name
                and existing.typespec == typespec
                and existing.default == default
                and existing.help == help
                and existing.choices == choices
            )
            if same_signature:
                return
            else:
                logger.warning("Over-riding existing option %s" % name)
        self.master.options.add_option(name, typespec, default, help, choices)

    def add_command(self, path: str, func: Callable) -> None:
        """Add a command to mitmproxy.

        Unless you are generating commands programatically,
        this API should be avoided. Decorate your function with `@mitmproxy.command.command` instead.
        """
        self.master.commands.add(path, func)


def traverse(chain):
    """
    Recursively traverse an addon chain.
    """
    for a in chain:
        yield a
        if hasattr(a, "addons"):
            yield from traverse(a.addons)


@dataclass
class LoadHook(hooks.Hook):
    """
    Called when an addon is first loaded. This event receives a Loader
    object, which contains methods for adding options and commands. This
    method is where the addon configures itself.
    """

    loader: Loader


class AddonManager:
    def __init__(self, master):
        self.lookup = {}
        self.chain = []
        self.master = master
        master.options.changed.connect(self._configure_all)

    def _configure_all(self, updated):
        self.trigger(hooks.ConfigureHook(updated))

    def clear(self):
        """
        Remove all addons.
        """
        for a in self.chain:
            self.invoke_addon_sync(a, hooks.DoneHook())
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
        api_changes = {
            # mitmproxy 6 -> mitmproxy 7
            "clientconnect": f"The clientconnect event has been removed, use client_connected instead",
            "clientdisconnect": f"The clientdisconnect event has been removed, use client_disconnected instead",
            "serverconnect": "The serverconnect event has been removed, use server_connect and server_connected instead",
            "serverdisconnect": f"The serverdisconnect event has been removed, use server_disconnected instead",
            # mitmproxy 8 -> mitmproxy 9
            "add_log": "The add_log event has been deprecated, use Python's builtin logging module instead",
        }
        for a in traverse([addon]):
            for old, msg in api_changes.items():
                if hasattr(a, old):
                    logger.warning(
                        f"{msg}. For more details, see https://docs.mitmproxy.org/dev/addons-api-changelog/."
                    )
            name = _get_name(a)
            if name in self.lookup:
                raise exceptions.AddonManagerError(
                    "An addon called '%s' already exists." % name
                )
        loader = Loader(self.master)
        self.invoke_addon_sync(addon, LoadHook(loader))
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
        self.invoke_addon_sync(addon, hooks.DoneHook())

    def __len__(self):
        return len(self.chain)

    def __str__(self):
        return pprint.pformat([str(i) for i in self.chain])

    def __contains__(self, item):
        name = _get_name(item)
        return name in self.lookup

    async def handle_lifecycle(self, event: hooks.Hook):
        """
        Handle a lifecycle event.
        """
        message = event.args()[0]

        await self.trigger_event(event)

        if isinstance(message, flow.Flow):
            await self.trigger_event(hooks.UpdateHook([message]))

    def _iter_hooks(self, addon, event: hooks.Hook):
        """
        Enumerate all hook callables belonging to the given addon
        """
        assert isinstance(event, hooks.Hook)
        for a in traverse([addon]):
            func = getattr(a, event.name, None)
            if func:
                if callable(func):
                    yield a, func
                elif isinstance(func, types.ModuleType):
                    # we gracefully exclude module imports with the same name as hooks.
                    # For example, a user may have "from mitmproxy import log" in an addon,
                    # which has the same name as the "log" hook. In this particular case,
                    # we end up in an error loop because we "log" this error.
                    pass
                else:
                    raise exceptions.AddonManagerError(
                        f"Addon handler {event.name} ({a}) not callable"
                    )

    async def invoke_addon(self, addon, event: hooks.Hook):
        """
        Asynchronously invoke an event on an addon and all its children.
        """
        for addon, func in self._iter_hooks(addon, event):
            res = func(*event.args())
            # Support both async and sync hook functions
            if res is not None and inspect.isawaitable(res):
                await res

    def invoke_addon_sync(self, addon, event: hooks.Hook):
        """
        Invoke an event on an addon and all its children.
        """
        for addon, func in self._iter_hooks(addon, event):
            if inspect.iscoroutinefunction(func):
                raise exceptions.AddonManagerError(
                    f"Async handler {event.name} ({addon}) cannot be called from sync context"
                )
            func(*event.args())

    async def trigger_event(self, event: hooks.Hook):
        """
        Asynchronously trigger an event across all addons.
        """
        for i in self.chain:
            try:
                with safecall():
                    await self.invoke_addon(i, event)
            except exceptions.AddonHalt:
                return

    def trigger(self, event: hooks.Hook):
        """
        Trigger an event across all addons.

        This API is discouraged and may be deprecated in the future.
        Use `trigger_event()` instead, which provides the same functionality but supports async hooks.
        """
        for i in self.chain:
            try:
                with safecall():
                    self.invoke_addon_sync(i, event)
            except exceptions.AddonHalt:
                return
