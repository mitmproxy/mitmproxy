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
import datetime

import blinker
import sortedcontainers

import mitmproxy.flow
from mitmproxy import flowfilter
from mitmproxy import exceptions

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

    def generate(self, f: mitmproxy.flow.Flow) -> typing.Any:  # pragma: no cover
        pass

    def refresh(self, f):
        k = self._key()
        old = self.view.settings[f][k]
        new = self.generate(f)
        if old != new:
            self.view._view.remove(f)
            self.view.settings[f][k] = new
            self.view._view.add(f)
            self.view.sig_view_refresh.send(self.view)

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
    def generate(self, f: mitmproxy.flow.Flow) -> datetime.datetime:
        return f.request.timestamp_start or 0


class OrderRequestMethod(_OrderKey):
    def generate(self, f: mitmproxy.flow.Flow) -> str:
        return f.request.method


class OrderRequestURL(_OrderKey):
    def generate(self, f: mitmproxy.flow.Flow) -> str:
        return f.request.url


class OrderKeySize(_OrderKey):
    def generate(self, f: mitmproxy.flow.Flow) -> int:
        s = 0
        if f.request.raw_content:
            s += len(f.request.raw_content)
        if f.response and f.response.raw_content:
            s += len(f.response.raw_content)
        return s


matchall = flowfilter.parse(".")


orders = [
    ("t", "time"),
    ("m", "method"),
    ("u", "url"),
    ("z", "size"),
]


class View(collections.Sequence):
    def __init__(self):
        super().__init__()
        self._store = {}
        self.filter = matchall
        # Should we show only marked flows?
        self.show_marked = False

        self.default_order = OrderRequestStart(self)
        self.orders = dict(
            time = self.default_order,
            method = OrderRequestMethod(self),
            url = OrderRequestURL(self),
            size = OrderKeySize(self),
        )
        self.order_key = self.default_order
        self.order_reversed = False
        self.focus_follow = False

        self._view = sortedcontainers.SortedListWithKey(key = self.order_key)

        # The sig_view* signals broadcast events that affect the view. That is,
        # an update to a flow in the store but not in the view does not trigger
        # a signal. All signals are called after the view has been updated.
        self.sig_view_update = blinker.Signal()
        self.sig_view_add = blinker.Signal()
        self.sig_view_remove = blinker.Signal()
        # Signals that the view should be refreshed completely
        self.sig_view_refresh = blinker.Signal()

        # The sig_store* signals broadcast events that affect the underlying
        # store. If a flow is removed from just the view, sig_view_remove is
        # triggered. If it is removed from the store while it is also in the
        # view, both sig_store_remove and sig_view_remove are triggered.
        self.sig_store_remove = blinker.Signal()
        # Signals that the store should be refreshed completely
        self.sig_store_refresh = blinker.Signal()

        self.focus = Focus(self)
        self.settings = Settings(self)

    def store_count(self):
        return len(self._store)

    def inbounds(self, index: int) -> bool:
        """
            Is this 0 <= index < len(self)
        """
        return 0 <= index < len(self)

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

    def __getitem__(self, offset) -> mitmproxy.flow.Flow:
        return self._view[self._rev(offset)]

    # Reflect some methods to the efficient underlying implementation

    def _bisect(self, f: mitmproxy.flow.Flow) -> int:
        v = self._view.bisect_right(f)
        return self._rev(v - 1) + 1

    def index(self, f: mitmproxy.flow.Flow, start: int = 0, stop: typing.Optional[int] = None) -> int:
        return self._rev(self._view.index(f, start, stop))

    def __contains__(self, f: mitmproxy.flow.Flow) -> bool:
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
        self.sig_view_refresh.send(self)

    # API
    def toggle_marked(self):
        self.show_marked = not self.show_marked
        self._refilter()

    def set_reversed(self, value: bool):
        self.order_reversed = value
        self.sig_view_refresh.send(self)

    def set_order(self, order_key: typing.Callable):
        """
            Sets the current view order.
        """
        self.order_key = order_key
        newview = sortedcontainers.SortedListWithKey(key=order_key)
        newview.update(self._view)
        self._view = newview

    def set_filter(self, flt: typing.Optional[flowfilter.TFilter]):
        """
            Sets the current view filter.
        """
        self.filter = flt or matchall
        self._refilter()

    def clear(self):
        """
            Clears both the store and view.
        """
        self._store.clear()
        self._view.clear()
        self.sig_view_refresh.send(self)
        self.sig_store_refresh.send(self)

    def add(self, f: mitmproxy.flow.Flow) -> bool:
        """
            Adds a flow to the state. If the flow already exists, it is
            ignored.
        """
        if f.id not in self._store:
            self._store[f.id] = f
            if self.filter(f):
                self._base_add(f)
                if self.focus_follow:
                    self.focus.flow = f
                self.sig_view_add.send(self, flow=f)

    def remove(self, f: mitmproxy.flow.Flow):
        """
            Removes the flow from the underlying store and the view.
        """
        if f.id in self._store:
            if f in self._view:
                self._view.remove(f)
                self.sig_view_remove.send(self, flow=f)
            del self._store[f.id]
            self.sig_store_remove.send(self, flow=f)

    def update(self, f: mitmproxy.flow.Flow):
        """
            Updates a flow. If the flow is not in the state, it's ignored.
        """
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
                    self._view.remove(f)
                    self.sig_view_remove.send(self, flow=f)
                except ValueError:
                    # The value was not in the view
                    pass

    def get_by_id(self, flow_id: str) -> typing.Optional[mitmproxy.flow.Flow]:
        """
        Get flow with the given id from the store.
        Returns None if the flow is not found.
        """
        return self._store.get(flow_id)

    # Event handlers
    def configure(self, opts, updated):
        if "filter" in updated:
            filt = None
            if opts.filter:
                filt = flowfilter.parse(opts.filter)
                if not filt:
                    raise exceptions.OptionsError(
                        "Invalid interception filter: %s" % opts.filter
                    )
            self.set_filter(filt)
        if "order" in updated:
            if opts.order is None:
                self.set_order(self.default_order)
            else:
                if opts.order not in self.orders:
                    raise exceptions.OptionsError(
                        "Unknown flow order: %s" % opts.order
                    )
                self.set_order(self.orders[opts.order])
        if "order_reversed" in updated:
            self.set_reversed(opts.order_reversed)
        if "focus_follow" in updated:
            self.focus_follow = opts.focus_follow

    def request(self, f):
        self.add(f)

    def error(self, f):
        self.update(f)

    def response(self, f):
        self.update(f)

    def intercept(self, f):
        self.update(f)

    def resume(self, f):
        self.update(f)

    def kill(self, f):
        self.update(f)


class Focus:
    """
        Tracks a focus element within a View.
    """
    def __init__(self, v: View) -> None:
        self.view = v
        self._flow = None  # type: mitmproxy.flow.Flow
        self.sig_change = blinker.Signal()
        if len(self.view):
            self.flow = self.view[0]
        v.sig_view_add.connect(self._sig_view_add)
        v.sig_view_remove.connect(self._sig_view_remove)
        v.sig_view_refresh.connect(self._sig_view_refresh)

    @property
    def flow(self) -> typing.Optional[mitmproxy.flow.Flow]:
        return self._flow

    @flow.setter
    def flow(self, f: typing.Optional[mitmproxy.flow.Flow]):
        if f is not None and f not in self.view:
            raise ValueError("Attempt to set focus to flow not in view")
        self._flow = f
        self.sig_change.send(self)

    @property
    def index(self) -> typing.Optional[int]:
        if self.flow:
            return self.view.index(self.flow)

    @index.setter
    def index(self, idx):
        if idx < 0 or idx > len(self.view) - 1:
            raise ValueError("Index out of view bounds")
        self.flow = self.view[idx]

    def _nearest(self, f, v):
        return min(v._bisect(f), len(v) - 1)

    def _sig_view_remove(self, view, flow):
        if len(view) == 0:
            self.flow = None
        elif flow is self.flow:
            self.flow = view[self._nearest(self.flow, view)]

    def _sig_view_refresh(self, view):
        if len(view) == 0:
            self.flow = None
        elif self.flow is None:
            self.flow = view[0]
        elif self.flow not in view:
            self.flow = view[self._nearest(self.flow, view)]

    def _sig_view_add(self, view, flow):
        # We only have to act if we don't have a focus element
        if not self.flow:
            self.flow = flow


class Settings(collections.Mapping):
    def __init__(self, view: View) -> None:
        self.view = view
        self._values = {}  # type: typing.MutableMapping[str, mitmproxy.flow.Flow]
        view.sig_store_remove.connect(self._sig_store_remove)
        view.sig_store_refresh.connect(self._sig_store_refresh)

    def __iter__(self) -> typing.Iterator:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, f: mitmproxy.flow.Flow) -> dict:
        if f.id not in self.view._store:
            raise KeyError
        return self._values.setdefault(f.id, {})

    def _sig_store_remove(self, view, flow):
        if flow.id in self._values:
            del self._values[flow.id]

    def _sig_store_refresh(self, view):
        for fid in list(self._values.keys()):
            if fid not in view._store:
                del self._values[fid]
