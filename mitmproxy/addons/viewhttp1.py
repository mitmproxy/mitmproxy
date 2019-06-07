"""
The View:

- Keeps track of a store of flows
- Maintains a filtered, ordered view onto that list of flows
- Exposes a number of signals so the view can be monitored
- Tracks focus within the view
- Exposes a settings store for flows that automatically expires if the flow is
  removed from the store.
"""
import collections
import typing

import blinker
import sortedcontainers

import mitmproxy.flow
from mitmproxy.addons import view
from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import command
from mitmproxy import connections
from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import http  # noqa

# The underlying sorted list implementation expects the sort key to be stable
# for the lifetime of the object. However, if we sort by size, for instance,
# the sort order changes as the flow progresses through its lifecycle. We
# address this through two means:
#
# - Let order keys cache the sort value by flow ID.
#
# - Add a facility to refresh items in the list by removing and re-adding them
# when they are updated.


class OrderTimestamp(view._OrderKey):
    def generate(self, f: http.HTTPFlow) -> int:
        return f.request.timestamp_start or 0


class OrderRequestMethod(view._OrderKey):
    def generate(self, f: http.HTTPFlow) -> str:
        return f.request.method


class OrderRequestURL(view._OrderKey):
    def generate(self, f: http.HTTPFlow) -> str:
        return f.request.url


class OrderKeySize(view._OrderKey):
    def generate(self, f: http.HTTPFlow) -> int:
        s = 0
        if f.request.raw_content:
            s += len(f.request.raw_content)
        if f.response and f.response.raw_content:
            s += len(f.response.raw_content)
        return s

orders = [
    ("t", "time"),
    ("m", "method"),
    ("u", "url"),
    ("z", "size"),
]

class ViewHttp1(view.View):
    def __init__(self):
        super().__init__()

        self.default_order = OrderTimestamp(self)
        self.orders = dict(
            time = OrderTimestamp(self), method = OrderRequestMethod(self),
            url = OrderRequestURL(self), size = OrderKeySize(self),
        )
        self.order_key = self.default_order
        self._view = sortedcontainers.SortedListWithKey(
            key = self.order_key
        )

    """ View API """

    # Focus
    @command.command("view.http1.focus.go")
    def go(self, dst: int) -> None:
        """
            Go to a specified offset. Positive offests are from the beginning of
            the view, negative from the end of the view, so that 0 is the first
            flow, -1 is the last flow.
        """
        super().go(dst)

    @command.command("view.http1.focus.next")
    def focus_next(self) -> None:
        """
            Set focus to the next flow.
        """
        super().focus_next()

    @command.command("view.http1.focus.prev")
    def focus_prev(self) -> None:
        """
            Set focus to the previous flow.
        """
        super().focus_prev()

    # Order
    @command.command("view.http1.order.options")
    def order_options(self) -> typing.Sequence[str]:
        """
            Choices supported by the view_order option.
        """
        return super().order_options()

    @command.command("view.http1.order.reverse")
    def set_reversed(self, value: bool) -> None:
        super().set_reversed(value)

    @command.command("view.http1.order.set")
    def set_order(self, order: str) -> None:
        """
            Sets the current view order.
        """
        super().set_order(order)

    @command.command("view.http1.order")
    def get_order(self) -> str:
        """
        Returns the current view order.
        """
        return super().get_order()

    # Filter
    @command.command("view.http1.filter.set")
    def set_filter_cmd(self, f: str) -> None:
        """
            Sets the current view filter.
        """
        super().set_filter_cmd(f)

    def set_filter(self, flt: typing.Optional[flowfilter.TFilter]):
        super().set_filter_cmd(f)

    # View Updates
    @command.command("view.http1.clear")
    def clear(self) -> None:
        """
            Clears both the store and view.
        """
        super().clear()

    @command.command("view.http1.clear_unmarked")
    def clear_not_marked(self) -> None:
        """
            Clears only the unmarked flows.
        """
        super().clear_not_marked()

    # View Settings
    @command.command("view.http1.settings.getval")
    def getvalue(self, f: mitmproxy.flow.Flow, key: str, default: str) -> str:
        """
            Get a value from the settings store for the specified flow.
        """
        return super().getvalue(f, key, default)

    @command.command("view.http1.settings.setval.toggle")
    def setvalue_toggle(
        self,
        flows: typing.Sequence[mitmproxy.flow.Flow],
        key: str
    ) -> None:
        """
            Toggle a boolean value in the settings store, setting the value to
            the string "true" or "false".
        """
        super().setvalue_toggle(flows, key)

    @command.command("view.http1.settings.setval")
    def setvalue(
        self,
        flows: typing.Sequence[mitmproxy.flow.Flow],
        key: str, value: str
    ) -> None:
        """
            Set a value in the settings store for the specified flows.
        """
        super().setvalue(flows, key)

    # Flows
    @command.command("view.http1.flow.duplicate")
    def duplicate(self, flows: typing.Sequence[mitmproxy.flow.Flow]) -> None:
        """
            Duplicates the specified flows, and sets the focus to the first
            duplicate.
        """
        super().duplicate(flows)

    @command.command("view.http1.flows.remove")
    def remove(self, flows: typing.Sequence[mitmproxy.flow.Flow]) -> None:
        """
            Removes the flow from the underlying store and the view.
        """
        super().remove(flows)

    @command.command("view.http1.flows.resolve")
    def resolve(self, spec: str) -> typing.Sequence[mitmproxy.flow.Flow]:
        """
            Resolve a flow list specification to an actual list of flows.
        """
        return super().resolve(spec)

    @command.command("view.http1.flows.create")
    def create(self, method: str, url: str) -> None:
        super().create(method, url)

    @command.command("view.http1.flows.load")
    def load_file(self, path: mitmproxy.types.Path) -> None:
        """
            Load flows into the view, without processing them with addons.
        """
        super().load_file(path)

    def add(self, flows: typing.Sequence[mitmproxy.flow.Flow]) -> None:
        """
            Adds a flow to the state. If the flow already exists, it is
            ignored.
        """
        for f in flows:
            if f.id not in self._store:
                self._store[f.id] = f
                if self.filter(f):
                    self._base_add(f)
                    if self.focus_follow:
                        self.focus.flow = f
                    self.sig_view_add.send(self, flow=f)

    def get_by_id(self, flow_id: str) -> typing.Optional[mitmproxy.flow.Flow]:
        """
            Get flow with the given id from the store.
            Returns None if the flow is not found.
        """
        return self._store.get(flow_id)

    # View Properties
    @command.command("view.http1.properties.length")
    def get_length(self) -> int:
        """
            Returns view length.
        """
        return len(self)

    @command.command("view.http1.properties.marked")
    def get_marked(self) -> bool:
        """
            Returns true if view is in marked mode.
        """
        return self.show_marked

    @command.command("view.http1.properties.marked.toggle")
    def toggle_marked(self) -> None:
        """
            Toggle whether to show marked views only.
        """
        super().toggle_marked()

    @command.command("view.http1.properties.inbounds")
    def inbounds(self, index: int) -> bool:
        """
            Is this 0 <= index < len(self)?
        """
        return super().inbounds(index)

    # Event handlers
    def configure(self, updated):
        if "view_filter" in updated:
            filt = None
            if ctx.options.view_filter:
                filt = flowfilter.parse(ctx.options.view_filter)
                if not filt:
                    raise exceptions.OptionsError(
                        "Invalid interception filter: %s" % ctx.options.view_filter
                    )
            self.set_filter(filt)
        if "view_order" in updated:
            if ctx.options.view_order not in self.orders:
                raise exceptions.OptionsError(
                    "Unknown flow order: %s" % ctx.options.view_order
                )
            self.set_order(ctx.options.view_order)
        if "view_order_reversed" in updated:
            self.set_reversed(ctx.options.view_order_reversed)
        if "console_focus_follow" in updated:
            self.focus_follow = ctx.options.console_focus_follow

    def request(self, f):
        self.add([f])

    def error(self, f):
        self.update([f])

    def response(self, f):
        self.update([f])

    def intercept(self, f):
        self.update([f])

    def resume(self, f):
        self.update([f])

    def kill(self, f):
        self.update([f])

    def update(self, flows: typing.Sequence[mitmproxy.flow.Flow]) -> None:
        """
            Updates a list of flows. If flow is not in the state, it's ignored.
        """
        for f in flows:
            if f.id in self._store:
                if self.filter(f):
                    if f not in self._view:
                        self._base_add(f)
                        if self.focus_follow:
                            self.focus.flow = f
                        self.sig_view_add.send(self, flow=f)
                    else:
                        # This is a tad complicated. The sortedcontainers
                        # implementation assumes that the order key is stable. If
                        # it changes mid-way Very Bad Things happen. We detect when
                        # this happens, and re-fresh the item.
                        self.order_key.refresh(f)
                        self.sig_view_update.send(self, flow=f)
                else:
                    try:
                        idx = self._view.index(f)
                    except ValueError:
                        pass  # The value was not in the view
                    else:
                        self._view.remove(f)
                        self.sig_view_remove.send(self, flow=f, index=idx)
