import re
from dataclasses import dataclass, is_dataclass, fields
from typing import ClassVar, Any, Dict, Type, Set, List, TYPE_CHECKING, Sequence

import mitmproxy.flow

if TYPE_CHECKING:
    import mitmproxy.addonmanager
    import mitmproxy.log


class EventHook:
    name: ClassVar[str]

    def args(self) -> List[Any]:
        args = []
        for field in fields(self):
            args.append(getattr(self, field.name))
        return args

    def __new__(cls, *args, **kwargs):
        if cls is EventHook:
            raise TypeError("MitmproxyEvent may not be instantiated directly.")
        if not is_dataclass(cls):
            raise TypeError("Subclass is not a dataclass.")
        return super().__new__(cls)

    def __init_subclass__(cls, **kwargs):
        # initialize .name attribute. HttpRequestHook -> http_request
        if cls.__dict__.get("name", None) is None:
            name = cls.__name__.replace("Hook", "").replace("Event", "")
            cls.name = re.sub('(?!^)([A-Z]+)', r'_\1', name).lower()
        if cls.name in all_events:
            other = all_events[cls.name]
            raise RuntimeError(f"Two conflicting event classes for {cls.name}: {cls} and {other}")
        if cls.name == "":
            return  # don't register Hook class.
        all_events[cls.name] = cls

        # define a custom hash and __eq__ function so that events are hashable and not comparable.
        cls.__hash__ = object.__hash__
        cls.__eq__ = object.__eq__


all_events: Dict[str, Type[EventHook]] = {}


@dataclass
class ConfigureEventHook(EventHook):
    """
    Called when configuration changes. The updated argument is a
    set-like object containing the keys of all changed options. This
    event is called during startup with all options in the updated set.
    """
    updated: Set[str]


@dataclass
class DoneEventHook(EventHook):
    """
    Called when the addon shuts down, either by being removed from
    the mitmproxy instance, or when mitmproxy itself shuts down. On
    shutdown, this event is called after the event loop is
    terminated, guaranteeing that it will be the final event an addon
    sees. Note that log handlers are shut down at this point, so
    calls to log functions will produce no output.
    """


@dataclass
class RunningEventHook(EventHook):
    """
    Called when the proxy is completely up and running. At this point,
    you can expect the proxy to be bound to a port, and all addons to be
    loaded.
    """


@dataclass
class UpdateEventHook(EventHook):
    """
    Update is called when one or more flow objects have been modified,
    usually from a different addon.
    """
    flows: Sequence[mitmproxy.flow.Flow]
