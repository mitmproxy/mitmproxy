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

import mitmproxy.viewitem
from mitmproxy.addons import view
from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import command
from mitmproxy import connections
from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import http2  # noqa

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
    def generate(self, f: http2.HTTP2Frame) -> int:
        return f.timestamp or 0


class OrderFrameType(view._OrderKey):
    def generate(self, f: http2.HTTP2Frame) -> str:
        return f.frame_type


class OrderStreamID(view._OrderKey):
    def generate(self, f: http2.HTTP2Frame) -> str:
        return f.frame_type


class OrderKeySize(view._OrderKey):
    def generate(self, f: http2.HTTP2Frame) -> int:
        s = 0
        if f.request.raw_content:
            s += len(f.request.raw_content)
        if f.response and f.response.raw_content:
            s += len(f.response.raw_content)
        return s


class ViewHttp2(view.View):
    def __init__(self):
        super().__init__()
        self.matchall = flowfilter.parse("~http2")
        self.base_orders = [
            ("t", "time"),
            ("f", "frametype"),
        ]

        self.default_order = OrderTimestamp(self)
        self.filter = self.matchall
        self.orders = dict(
            time = OrderTimestamp(self), method = OrderStreamID(self),
            url = OrderFrameType(self), size = OrderKeySize(self),
        )
        self.order_key = self.default_order
        self._view = sortedcontainers.SortedListWithKey(
            key = self.order_key
        )

    @property
    def flow_type(self) -> str:
        return "http2"

    """ View API """

    # Focus
    @command.command("view.http2.focus.go")
    def go(self, dst: int) -> None:
        """
            Go to a specified offset. Positive offests are from the beginning of
            the view, negative from the end of the view, so that 0 is the first
            flow, -1 is the last flow.
        """
        super().go(dst)

    @command.command("view.http2.focus.next")
    def focus_next(self) -> None:
        """
            Set focus to the next flow.
        """
        super().focus_next()

    @command.command("view.http2.focus.prev")
    def focus_prev(self) -> None:
        """
            Set focus to the previous flow.
        """
        super().focus_prev()

    # Order
    @command.command("view.http2.order.options")
    def order_options(self) -> typing.Sequence[str]:
        """
            Choices supported by the view_order option.
        """
        return super().order_options()

    @command.command("view.http2.order.reverse")
    def set_reversed(self, value: bool) -> None:
        super().set_reversed(value)

    @command.command("view.http2.order.set")
    def set_order(self, order: str) -> None:
        """
            Sets the current view order.
        """
        super().set_order(order)

    @command.command("view.http2.order")
    def get_order(self) -> str:
        """
        Returns the current view order.
        """
        return super().get_order()

    # Filter
    @command.command("view.http2.filter.set")
    def set_filter_cmd(self, f: str) -> None:
        """
            Sets the current view filter.
        """
        super().set_filter_cmd(f)

    @command.command("view.http2.filtred_view.add")
    def add_filtred_view(self, f: str, n: str) -> None:
        super().add_filtred_view(f, n)

    # View Updates
    @command.command("view.http2.clear")
    def clear(self) -> None:
        """
            Clears both the store and view.
        """
        super().clear()

    @command.command("view.http2.clear_unmarked")
    def clear_not_marked(self) -> None:
        """
            Clears only the unmarked flows.
        """
        super().clear_not_marked()

    # View Settings
    @command.command("view.http2.settings.getval")
    def getvalue(self, f: mitmproxy.viewitem.ViewItem, key: str, default: str) -> str:
        """
            Get a value from the settings store for the specified flow.
        """
        return super().getvalue(f, key, default)

    @command.command("view.http2.settings.setval.toggle")
    def setvalue_toggle(
        self,
        flows: typing.Sequence[mitmproxy.viewitem.ViewItem],
        key: str
    ) -> None:
        """
            Toggle a boolean value in the settings store, setting the value to
            the string "true" or "false".
        """
        super().setvalue_toggle(flows, key)

    @command.command("view.http2.settings.setval")
    def setvalue(
        self,
        flows: typing.Sequence[mitmproxy.viewitem.ViewItem],
        key: str, value: str
    ) -> None:
        """
            Set a value in the settings store for the specified flows.
        """
        super().setvalue(flows, key)

    # Flows
    @command.command("view.http2.flows.duplicate")
    def duplicate(self, flows: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Duplicates the specified flows, and sets the focus to the first
            duplicate.
        """
        super().duplicate(flows)

    @command.command("view.http2.flows.remove")
    def remove(self, flows: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Removes the flow from the underlying store and the view.
        """
        super().remove(flows)

    @command.command("view.http2.flows.resolve")
    def resolve(self, spec: str) -> typing.Sequence[mitmproxy.viewitem.ViewItem]:
        """
            Resolve a flow list specification to an actual list of flows.
        """
        return super().resolve(spec)

    @command.command("view.http2.flows.create")
    def create(self, method: str, url: str) -> None:
        super().create(method, url)

    @command.command("view.http2.flows.load")
    def load_file(self, path: mitmproxy.types.Path) -> None:
        """
            Load flows into the view, without processing them with addons.
        """
        super().load_file(path)

    # View Properties
    @command.command("view.http2.properties.length")
    def get_length(self) -> int:
        """
            Returns view length.
        """
        return super().get_length()

    @command.command("view.http2.properties.marked")
    def get_marked(self) -> bool:
        """
            Returns true if view is in marked mode.
        """
        return super().get_marked()

    @command.command("view.http2.properties.marked.toggle")
    def toggle_marked(self) -> None:
        """
            Toggle whether to show marked views only.
        """
        super().toggle_marked()

    @command.command("view.http2.properties.inbounds")
    def inbounds(self, index: int, name: str = None) -> bool:
        """
            Is this 0 <= index < len(self)
        """
        return super().inbounds(index, name)

    # Event handlers

    def http2_start(self, flow: mitmproxy.http2.HTTP2Frame):
        """
            A HTTP/2 connection has started.
        """

    def http2_frame(self, flow: mitmproxy.http2.HTTP2Frame):
        """
            A HTTP/2 connection has received a message. The most recent message
            will be flow.messages[-1]. The message is user-modifiable.
        """
        self.add([flow.messages[-1]])

    def http2_error(self, flow: mitmproxy.http2.HTTP2Frame):
        """
            A HTTP/2 error has occurred.
        """

    def http2_end(self, flow: mitmproxy.http2.HTTP2Frame):
        """
            A HTTP/2 connection has ended.
        """
