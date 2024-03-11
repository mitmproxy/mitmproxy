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
import logging
import re
from collections.abc import Iterator
from collections.abc import MutableMapping
from collections.abc import Sequence
from typing import Any
from typing import Optional

import sortedcontainers

import mitmproxy.flow
from mitmproxy import command
from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy import dns
from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import hooks
from mitmproxy import http
from mitmproxy import io
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy.log import ALERT
from mitmproxy.utils import human
from mitmproxy.utils import signals

# The underlying sorted list implementation expects the sort key to be stable
# for the lifetime of the object. However, if we sort by size, for instance,
# the sort order changes as the flow progresses through its lifecycle. We
# address this through two means:
#
# - Let order keys cache the sort value by flow ID.
#
# - Add a facility to refresh items in the list by removing and re-adding them
# when they are updated.


class _OrderKey:
    def __init__(self, view):
        self.view = view

    def generate(self, f: mitmproxy.flow.Flow) -> Any:  # pragma: no cover
        pass

    def refresh(self, f):
        k = self._key()
        old = self.view.settings[f][k]
        new = self.generate(f)
        if old != new:
            self.view._view.remove(f)
            self.view.settings[f][k] = new
            self.view._view.add(f)
            self.view.sig_view_refresh.send()

    def _key(self):
        return "_order_%s" % id(self)

    def __call__(self, f):
        if f.id in self.view._store:
            k = self._key()
            s = self.view.settings[f]
            if k in s:
                return s[k]
            val = self.generate(f)
            s[k] = val
            return val
        else:
            return self.generate(f)


class OrderRequestStart(_OrderKey):
    def generate(self, f: mitmproxy.flow.Flow) -> float:
        return f.timestamp_created


class OrderRequestMethod(_OrderKey):
    def generate(self, f: mitmproxy.flow.Flow) -> str:
        if isinstance(f, http.HTTPFlow):
            return f.request.method
        elif isinstance(f, (tcp.TCPFlow, udp.UDPFlow)):
            return f.type.upper()
        elif isinstance(f, dns.DNSFlow):
            return dns.op_codes.to_str(f.request.op_code)
        else:
            raise NotImplementedError()


class OrderRequestURL(_OrderKey):
    def generate(self, f: mitmproxy.flow.Flow) -> str:
        if isinstance(f, http.HTTPFlow):
            return f.request.url
        elif isinstance(f, (tcp.TCPFlow, udp.UDPFlow)):
            return human.format_address(f.server_conn.address)
        elif isinstance(f, dns.DNSFlow):
            return f.request.questions[0].name if f.request.questions else ""
        else:
            raise NotImplementedError()


class OrderKeySize(_OrderKey):
    def generate(self, f: mitmproxy.flow.Flow) -> int:
        if isinstance(f, http.HTTPFlow):
            size = 0
            if f.request.raw_content:
                size += len(f.request.raw_content)
            if f.response and f.response.raw_content:
                size += len(f.response.raw_content)
            return size
        elif isinstance(f, (tcp.TCPFlow, udp.UDPFlow)):
            size = 0
            for message in f.messages:
                size += len(message.content)
            return size
        elif isinstance(f, dns.DNSFlow):
            return f.response.size if f.response else 0
        else:
            raise NotImplementedError()


orders = [
    ("t", "time"),
    ("m", "method"),
    ("u", "url"),
    ("z", "size"),
]


def _signal_with_flow(flow: mitmproxy.flow.Flow) -> None: ...


def _sig_view_remove(flow: mitmproxy.flow.Flow, index: int) -> None: ...


class View(collections.abc.Sequence):
    def __init__(self) -> None:
        super().__init__()
        self._store: collections.OrderedDict[str, mitmproxy.flow.Flow] = (
            collections.OrderedDict()
        )
        self.filter = flowfilter.match_all
        # Should we show only marked flows?
        self.show_marked = False

        self.default_order = OrderRequestStart(self)
        self.orders = dict(
            time=OrderRequestStart(self),
            method=OrderRequestMethod(self),
            url=OrderRequestURL(self),
            size=OrderKeySize(self),
        )
        self.order_key: _OrderKey = self.default_order
        self.order_reversed = False
        self.focus_follow = False

        self._view = sortedcontainers.SortedListWithKey(key=self.order_key)

        # The sig_view* signals broadcast events that affect the view. That is,
        # an update to a flow in the store but not in the view does not trigger
        # a signal. All signals are called after the view has been updated.
        self.sig_view_update = signals.SyncSignal(_signal_with_flow)
        self.sig_view_add = signals.SyncSignal(_signal_with_flow)
        self.sig_view_remove = signals.SyncSignal(_sig_view_remove)
        # Signals that the view should be refreshed completely
        self.sig_view_refresh = signals.SyncSignal(lambda: None)

        # The sig_store* signals broadcast events that affect the underlying
        # store. If a flow is removed from just the view, sig_view_remove is
        # triggered. If it is removed from the store while it is also in the
        # view, both sig_store_remove and sig_view_remove are triggered.
        self.sig_store_remove = signals.SyncSignal(_signal_with_flow)
        # Signals that the store should be refreshed completely
        self.sig_store_refresh = signals.SyncSignal(lambda: None)

        self.focus = Focus(self)
        self.settings = Settings(self)

    def load(self, loader):
        loader.add_option(
            "view_filter", Optional[str], None, "Limit the view to matching flows."
        )
        loader.add_option(
            "view_order",
            str,
            "time",
            "Flow sort order.",
            choices=list(map(lambda c: c[1], orders)),
        )
        loader.add_option(
            "view_order_reversed", bool, False, "Reverse the sorting order."
        )
        loader.add_option(
            "console_focus_follow", bool, False, "Focus follows new flows."
        )

    def store_count(self):
        return len(self._store)

    def _rev(self, idx: int) -> int:
        """
        Reverses an index, if needed
        """
        if self.order_reversed:
            if idx < 0:
                idx = -idx - 1
            else:
                idx = len(self._view) - idx - 1
                if idx < 0:
                    raise IndexError
        return idx

    def __len__(self):
        return len(self._view)

    def __getitem__(self, offset) -> Any:
        return self._view[self._rev(offset)]

    # Reflect some methods to the efficient underlying implementation

    def _bisect(self, f: mitmproxy.flow.Flow) -> int:
        v = self._view.bisect_right(f)
        return self._rev(v - 1) + 1

    def index(
        self, f: mitmproxy.flow.Flow, start: int = 0, stop: int | None = None
    ) -> int:
        return self._rev(self._view.index(f, start, stop))

    def __contains__(self, f: Any) -> bool:
        return self._view.__contains__(f)

    def _order_key_name(self):
        return "_order_%s" % id(self.order_key)

    def _base_add(self, f):
        self.settings[f][self._order_key_name()] = self.order_key(f)
        self._view.add(f)

    def _refilter(self):
        self._view.clear()
        for i in self._store.values():
            if self.show_marked and not i.marked:
                continue
            if self.filter(i):
                self._base_add(i)
        self.sig_view_refresh.send()

    """ View API """

    # Focus
    @command.command("view.focus.go")
    def go(self, offset: int) -> None:
        """
        Go to a specified offset. Positive offests are from the beginning of
        the view, negative from the end of the view, so that 0 is the first
        flow, -1 is the last flow.
        """
        if len(self) == 0:
            return
        if offset < 0:
            offset = len(self) + offset
        if offset < 0:
            offset = 0
        if offset > len(self) - 1:
            offset = len(self) - 1
        self.focus.flow = self[offset]

    @command.command("view.focus.next")
    def focus_next(self) -> None:
        """
        Set focus to the next flow.
        """
        if self.focus.index is not None:
            idx = self.focus.index + 1
            if self.inbounds(idx):
                self.focus.flow = self[idx]
        else:
            pass

    @command.command("view.focus.prev")
    def focus_prev(self) -> None:
        """
        Set focus to the previous flow.
        """
        if self.focus.index is not None:
            idx = self.focus.index - 1
            if self.inbounds(idx):
                self.focus.flow = self[idx]
        else:
            pass

    # Order
    @command.command("view.order.options")
    def order_options(self) -> Sequence[str]:
        """
        Choices supported by the view_order option.
        """
        return list(sorted(self.orders.keys()))

    @command.command("view.order.reverse")
    def set_reversed(self, boolean: bool) -> None:
        self.order_reversed = boolean
        self.sig_view_refresh.send()

    @command.command("view.order.set")
    def set_order(self, order_key: str) -> None:
        """
        Sets the current view order.
        """
        if order_key not in self.orders:
            raise exceptions.CommandError("Unknown flow order: %s" % order_key)
        key = self.orders[order_key]
        self.order_key = key
        newview = sortedcontainers.SortedListWithKey(key=key)
        newview.update(self._view)
        self._view = newview

    @command.command("view.order")
    def get_order(self) -> str:
        """
        Returns the current view order.
        """
        order = ""
        for k in self.orders.keys():
            if self.order_key == self.orders[k]:
                order = k
        return order

    # Filter
    @command.command("view.filter.set")
    def set_filter_cmd(self, filter_expr: str) -> None:
        """
        Sets the current view filter.
        """
        filt = None
        if filter_expr:
            try:
                filt = flowfilter.parse(filter_expr)
            except ValueError as e:
                raise exceptions.CommandError(str(e)) from e
        self.set_filter(filt)

    def set_filter(self, flt: flowfilter.TFilter | None):
        self.filter = flt or flowfilter.match_all
        self._refilter()

    # View Updates
    @command.command("view.clear")
    def clear(self) -> None:
        """
        Clears both the store and view.
        """
        self._store.clear()
        self._view.clear()
        self.sig_view_refresh.send()
        self.sig_store_refresh.send()

    @command.command("view.clear_unmarked")
    def clear_not_marked(self) -> None:
        """
        Clears only the unmarked flows.
        """
        for flow in self._store.copy().values():
            if not flow.marked:
                self._store.pop(flow.id)

        self._refilter()
        self.sig_store_refresh.send()

    # View Settings
    @command.command("view.settings.getval")
    def getvalue(self, flow: mitmproxy.flow.Flow, key: str, default: str) -> str:
        """
        Get a value from the settings store for the specified flow.
        """
        return self.settings[flow].get(key, default)

    @command.command("view.settings.setval.toggle")
    def setvalue_toggle(self, flows: Sequence[mitmproxy.flow.Flow], key: str) -> None:
        """
        Toggle a boolean value in the settings store, setting the value to
        the string "true" or "false".
        """
        updated = []
        for f in flows:
            current = self.settings[f].get("key", "false")
            self.settings[f][key] = "false" if current == "true" else "true"
            updated.append(f)
        ctx.master.addons.trigger(hooks.UpdateHook(updated))

    @command.command("view.settings.setval")
    def setvalue(
        self, flows: Sequence[mitmproxy.flow.Flow], key: str, value: str
    ) -> None:
        """
        Set a value in the settings store for the specified flows.
        """
        updated = []
        for f in flows:
            self.settings[f][key] = value
            updated.append(f)
        ctx.master.addons.trigger(hooks.UpdateHook(updated))

    # Flows
    @command.command("view.flows.duplicate")
    def duplicate(self, flows: Sequence[mitmproxy.flow.Flow]) -> None:
        """
        Duplicates the specified flows, and sets the focus to the first
        duplicate.
        """
        dups = [f.copy() for f in flows]
        if dups:
            self.add(dups)
            self.focus.flow = dups[0]
            logging.log(ALERT, "Duplicated %s flows" % len(dups))

    @command.command("view.flows.remove")
    def remove(self, flows: Sequence[mitmproxy.flow.Flow]) -> None:
        """
        Removes the flow from the underlying store and the view.
        """
        for f in flows:
            if f.id in self._store:
                if f.killable:
                    f.kill()
                if f in self._view:
                    # We manually pass the index here because multiple flows may have the same
                    # sorting key, and we cannot reconstruct the index from that.
                    idx = self._view.index(f)
                    self._view.remove(f)
                    self.sig_view_remove.send(flow=f, index=idx)
                del self._store[f.id]
                self.sig_store_remove.send(flow=f)
        if len(flows) > 1:
            logging.log(ALERT, "Removed %s flows" % len(flows))

    @command.command("view.flows.resolve")
    def resolve(self, flow_spec: str) -> Sequence[mitmproxy.flow.Flow]:
        """
        Resolve a flow list specification to an actual list of flows.
        """
        if flow_spec == "@all":
            return [i for i in self._store.values()]
        if flow_spec == "@focus":
            return [self.focus.flow] if self.focus.flow else []
        elif flow_spec == "@shown":
            return [i for i in self]
        elif flow_spec == "@hidden":
            return [i for i in self._store.values() if i not in self._view]
        elif flow_spec == "@marked":
            return [i for i in self._store.values() if i.marked]
        elif flow_spec == "@unmarked":
            return [i for i in self._store.values() if not i.marked]
        elif re.match(r"@[0-9a-f\-,]{36,}", flow_spec):
            ids = flow_spec[1:].split(",")
            return [i for i in self._store.values() if i.id in ids]
        else:
            try:
                filt = flowfilter.parse(flow_spec)
            except ValueError as e:
                raise exceptions.CommandError(str(e)) from e
            return [i for i in self._store.values() if filt(i)]

    @command.command("view.flows.create")
    def create(self, method: str, url: str) -> None:
        try:
            req = http.Request.make(method.upper(), url)
        except ValueError as e:
            raise exceptions.CommandError("Invalid URL: %s" % e)

        c = connection.Client(
            peername=("", 0),
            sockname=("", 0),
            timestamp_start=req.timestamp_start - 0.0001,
        )
        s = connection.Server(address=(req.host, req.port))

        f = http.HTTPFlow(c, s)
        f.request = req
        f.request.headers["Host"] = req.host
        self.add([f])

    @command.command("view.flows.load")
    def load_file(self, path: mitmproxy.types.Path) -> None:
        """
        Load flows into the view, without processing them with addons.
        """
        try:
            with open(path, "rb") as f:
                for i in io.FlowReader(f).stream():
                    # Do this to get a new ID, so we can load the same file N times and
                    # get new flows each time. It would be more efficient to just have a
                    # .newid() method or something.
                    self.add([i.copy()])
        except OSError as e:
            logging.error(e.strerror)
        except exceptions.FlowReadException as e:
            logging.error(str(e))

    def add(self, flows: Sequence[mitmproxy.flow.Flow]) -> None:
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
                    self.sig_view_add.send(flow=f)

    def get_by_id(self, flow_id: str) -> mitmproxy.flow.Flow | None:
        """
        Get flow with the given id from the store.
        Returns None if the flow is not found.
        """
        return self._store.get(flow_id)

    # View Properties
    @command.command("view.properties.length")
    def get_length(self) -> int:
        """
        Returns view length.
        """
        return len(self)

    @command.command("view.properties.marked")
    def get_marked(self) -> bool:
        """
        Returns true if view is in marked mode.
        """
        return self.show_marked

    @command.command("view.properties.marked.toggle")
    def toggle_marked(self) -> None:
        """
        Toggle whether to show marked views only.
        """
        self.show_marked = not self.show_marked
        self._refilter()

    @command.command("view.properties.inbounds")
    def inbounds(self, index: int) -> bool:
        """
        Is this 0 <= index < len(self)?
        """
        return 0 <= index < len(self)

    # Event handlers
    def configure(self, updated):
        if "view_filter" in updated:
            filt = None
            if ctx.options.view_filter:
                try:
                    filt = flowfilter.parse(ctx.options.view_filter)
                except ValueError as e:
                    raise exceptions.OptionsError(str(e)) from e
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

    def requestheaders(self, f):
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

    def tcp_start(self, f):
        self.add([f])

    def tcp_message(self, f):
        self.update([f])

    def tcp_error(self, f):
        self.update([f])

    def tcp_end(self, f):
        self.update([f])

    def udp_start(self, f):
        self.add([f])

    def udp_message(self, f):
        self.update([f])

    def udp_error(self, f):
        self.update([f])

    def udp_end(self, f):
        self.update([f])

    def dns_request(self, f):
        self.add([f])

    def dns_response(self, f):
        self.update([f])

    def dns_error(self, f):
        self.update([f])

    def update(self, flows: Sequence[mitmproxy.flow.Flow]) -> None:
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
                        self.sig_view_add.send(flow=f)
                    else:
                        # This is a tad complicated. The sortedcontainers
                        # implementation assumes that the order key is stable. If
                        # it changes mid-way Very Bad Things happen. We detect when
                        # this happens, and re-fresh the item.
                        self.order_key.refresh(f)
                        self.sig_view_update.send(flow=f)
                else:
                    try:
                        idx = self._view.index(f)
                    except ValueError:
                        pass  # The value was not in the view
                    else:
                        self._view.remove(f)
                        self.sig_view_remove.send(flow=f, index=idx)


class Focus:
    """
    Tracks a focus element within a View.
    """

    def __init__(self, v: View) -> None:
        self.view = v
        self._flow: mitmproxy.flow.Flow | None = None
        self.sig_change = signals.SyncSignal(lambda: None)
        if len(self.view):
            self.flow = self.view[0]
        v.sig_view_add.connect(self._sig_view_add)
        v.sig_view_remove.connect(self._sig_view_remove)
        v.sig_view_refresh.connect(self._sig_view_refresh)

    @property
    def flow(self) -> mitmproxy.flow.Flow | None:
        return self._flow

    @flow.setter
    def flow(self, f: mitmproxy.flow.Flow | None):
        if f is not None and f not in self.view:
            raise ValueError("Attempt to set focus to flow not in view")
        self._flow = f
        self.sig_change.send()

    @property
    def index(self) -> int | None:
        if self.flow:
            return self.view.index(self.flow)
        return None

    @index.setter
    def index(self, idx):
        if idx < 0 or idx > len(self.view) - 1:
            raise ValueError("Index out of view bounds")
        self.flow = self.view[idx]

    def _nearest(self, f, v):
        return min(v._bisect(f), len(v) - 1)

    def _sig_view_remove(self, flow, index):
        if len(self.view) == 0:
            self.flow = None
        elif flow is self.flow:
            self.index = min(index, len(self.view) - 1)

    def _sig_view_refresh(self):
        if len(self.view) == 0:
            self.flow = None
        elif self.flow is None:
            self.flow = self.view[0]
        elif self.flow not in self.view:
            self.flow = self.view[self._nearest(self.flow, self.view)]

    def _sig_view_add(self, flow):
        # We only have to act if we don't have a focus element
        if not self.flow:
            self.flow = flow


class Settings(collections.abc.Mapping):
    def __init__(self, view: View) -> None:
        self.view = view
        self._values: MutableMapping[str, dict] = {}
        view.sig_store_remove.connect(self._sig_store_remove)
        view.sig_store_refresh.connect(self._sig_store_refresh)

    def __iter__(self) -> Iterator:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, f: mitmproxy.flow.Flow) -> dict:
        if f.id not in self.view._store:
            raise KeyError
        return self._values.setdefault(f.id, {})

    def _sig_store_remove(self, flow):
        if flow.id in self._values:
            del self._values[flow.id]

    def _sig_store_refresh(self):
        for fid in list(self._values.keys()):
            if fid not in self.view._store:
                del self._values[fid]
