"""
The View:

- Keeps track of a store of viewitem
- Maintains a filtered, ordered view onto that list of viewitems
- Exposes a number of signals so the view can be monitored
- Tracks focus within the view
- Exposes a settings store for viewitems that automatically expires if the viewitem is
  removed from the store.
"""
from mitmproxy import command
from mitmproxy import connections
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import http  # noqa
from mitmproxy import io
from mitmproxy.addons import view
import mitmproxy.viewitem
import typing

import sortedcontainers


# The underlying sorted list implementation expects the sort key to be stable
# for the lifetime of the object. However, if we sort by size, for instance,
# the sort order changes as the viewitem progresses through its lifecycle. We
# address this through two means:
#
# - Let order keys cache the sort value by viewitem ID.
#
# - Add a facility to refresh items in the list by removing and re-adding them
# when they are updated.
class OrderRequestStart(view._OrderKey):
    def generate(self, i: http.HTTPFlow) -> int:
        return i.request.timestamp_start or 0


class OrderRequestMethod(view._OrderKey):
    def generate(self, i: http.HTTPFlow) -> str:
        return i.request.method


class OrderRequestURL(view._OrderKey):
    def generate(self, i: http.HTTPFlow) -> str:
        return i.request.url


class OrderKeySize(view._OrderKey):
    def generate(self, i: http.HTTPFlow) -> int:
        s = 0
        if i.request.raw_content:
            s += len(i.request.raw_content)
        if i.response and i.response.raw_content:
            s += len(i.response.raw_content)
        return s


class ViewHttp1(view.View):
    def __init__(self):
        super().__init__()
        self.matchall = flowfilter.parse(".")
        self.base_orders = [
            ("t", "time"),
            ("m", "method"),
            ("u", "url"),
            ("z", "size"),
        ]

        self.default_order = OrderRequestStart(self)
        self.filter = self.matchall
        self.orders = dict(
            time = OrderRequestStart(self), method = OrderRequestMethod(self),
            url = OrderRequestURL(self), size = OrderKeySize(self),
        )
        self.order_key = self.default_order
        self._view = sortedcontainers.SortedListWithKey(
            key = self.order_key
        )

    @property
    def flow_type(self) -> str:
        return "http1"

    """ View API """

    # Focus
    @command.command("view.http1.focus.go")
    def go(self, dst: int) -> None:
        """
            Go to a specified offset. Positive offests are from the beginning of
            the view, negative from the end of the view, so that 0 is the first
            viewitem, -1 is the last viewitem.
        """
        super().go(dst)

    @command.command("view.http1.focus.next")
    def focus_next(self) -> None:
        """
            Set focus to the next viewitem.
        """
        super().focus_next()

    @command.command("view.http1.focus.prev")
    def focus_prev(self) -> None:
        """
            Set focus to the previous viewitem.
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

    @command.command("view.http1.filtred_view.add")
    def add_filtred_view(self, f: str, n: str) -> None:
        super().add_filtred_view(f, n)

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
            Clears only the unmarked viewitems.
        """
        super().clear_not_marked()

    # View Settings
    @command.command("view.http1.settings.getval")
    def getvalue(self, i: mitmproxy.viewitem.ViewItem, key: str, default: str) -> str:
        """
            Get a value from the settings store for the specified viewitem.
        """
        return super().getvalue(i, key, default)

    @command.command("view.http1.settings.setval.toggle")
    def setvalue_toggle(
        self,
        viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem],
        key: str
    ) -> None:
        """
            Toggle a boolean value in the settings store, setting the value to
            the string "true" or "false".
        """
        super().setvalue_toggle(viewitems, key)

    @command.command("view.http1.settings.setval")
    def setvalue(
        self,
        viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem],
        key: str, value: str
    ) -> None:
        """
            Set a value in the settings store for the specified items.
        """
        super().setvalue(viewitems, key, value)

    # Flows
    @command.command("view.http1.items.duplicate")
    def duplicate(self, viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Duplicates the specified items, and sets the focus to the first
            duplicate.
        """
        super().duplicate(viewitems)

    @command.command("view.http1.items.remove")
    def remove(self, viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Removes the item from the underlying store and the view.
        """
        super().remove(viewitems)

    @command.command("view.http1.items.resolve")
    def resolve(self, spec: str) -> typing.Sequence[mitmproxy.viewitem.ViewItem]:
        """
            Resolve an item list specification to an actual list of items.
        """
        return super().resolve(spec)

    @command.command("view.http1.items.create")
    def create(self, method: str, url: str) -> None:
        try:
            req = http.HTTPRequest.make(method.upper(), url)
        except ValueError as e:
            raise exceptions.CommandError("Invalid URL: %s" % e)
        c = connections.ClientConnection.make_dummy(("", 0))
        s = connections.ServerConnection.make_dummy((req.host, req.port))
        i = http.HTTPFlow(c, s)
        i.request = req
        i.request.headers["Host"] = req.host
        self.add([i])

    @command.command("view.http1.items.load")
    def load_file(self, path: mitmproxy.types.Path) -> None:
        """
            Load viewitems into the view, without processing them with addons.
        """
        try:
            with open(path, "rb") as f:
                for i in io.FlowReader(f).stream():
                    # Do this to get a new ID, so we can load the same file N times and
                    # get new viewitem each time. It would be more efficient to just have a
                    # .newid() method or something.
                    self.add([i.copy()])
        except IOError as e:
            ctx.log.error(e.strerror)
        except exceptions.FlowReadException as e:
            ctx.log.error(str(e))

    # View Properties
    @command.command("view.http1.properties.length")
    def get_length(self) -> int:
        """
            Returns view length.
        """
        return super().get_length()

    @command.command("view.http1.properties.marked")
    def get_marked(self) -> bool:
        """
            Returns true if view is in marked mode.
        """
        return super().get_marked()

    @command.command("view.http1.properties.marked.toggle")
    def toggle_marked(self) -> None:
        """
            Toggle whether to show marked views only.
        """
        super().toggle_marked()

    @command.command("view.http1.properties.inbounds")
    def inbounds(self, index: int, name: str = None) -> bool:
        """
            Is this 0 <= index < len(self)
        """
        return super().inbounds(index, name)

    # Event handlers
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
