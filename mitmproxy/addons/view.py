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


def key_request_start(f: mitmproxy.flow.Flow) -> datetime.datetime:
    return f.request.timestamp_start or 0


def key_request_method(f: mitmproxy.flow.Flow) -> str:
    return f.request.method


def key_request_url(f: mitmproxy.flow.Flow) -> str:
    return f.request.url


def key_size(f: mitmproxy.flow.Flow) -> int:
    s = 0
    if f.request.raw_content:
        s += len(f.request.raw_content)
    if f.response and f.response.raw_content:
        s += len(f.response.raw_content)
    return s


orders = [
    ("t", "time", key_request_start),
    ("m", "method", key_request_method),
    ("u", "url", key_request_url),
    ("z", "size", key_size),
]


matchall = flowfilter.parse(".")


class View(collections.Sequence):
    def __init__(self):
        super().__init__()
        self._store = {}
        self.filter = matchall
        # Should we show only marked flows?
        self.show_marked = False
        self.order_key = key_request_start
        self.order_reversed = False
        self._view = sortedcontainers.SortedListWithKey(key = self.order_key)

        # These signals broadcast events that affect the view. That is, an
        # update to a flow in the store but not in the view does not trigger a
        # signal. All signals are called after the view has been updated.
        self.sig_update = blinker.Signal()
        self.sig_add = blinker.Signal()
        self.sig_remove = blinker.Signal()
        # Signals that the view should be refreshed completely
        self.sig_refresh = blinker.Signal()

        self.focus = Focus(self)
        self.settings = Settings(self)

    def store_count(self):
        return len(self._store)

    def inbounds(self, index: int) -> bool:
        """
            Is this index >= 0 and < len(self)
        """
        return index >= 0 and index < len(self)

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

    def bisect(self, f: mitmproxy.flow.Flow) -> int:
        v = self._view.bisect(f)
        # Bisect returns an item to the RIGHT of the existing entries.
        if v == 0:
            return v
        return self._rev(v - 1) + 1

    def index(self, f: mitmproxy.flow.Flow) -> int:
        return self._rev(self._view.index(f))

    def _refilter(self):
        self._view.clear()
        for i in self._store.values():
            if self.show_marked and not i.marked:
                continue
            if self.filter(i):
                self._view.add(i)
        self.sig_refresh.send(self)

    # API
    def toggle_marked(self):
        self.show_marked = not self.show_marked
        self._refilter()

    def set_reversed(self, value: bool):
        self.order_reversed = value
        self.sig_refresh.send(self)

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
            Clears both the state and view.
        """
        self._store.clear()
        self._view.clear()
        self.sig_refresh.send(self)

    def add(self, f: mitmproxy.flow.Flow):
        """
            Adds a flow to the state. If the flow already exists, it is
            ignored.
        """
        if f.id not in self._store:
            self._store[f.id] = f
            if self.filter(f):
                self._view.add(f)
                self.sig_add.send(self, flow=f)

    def remove(self, f: mitmproxy.flow.Flow):
        """
            Removes the flow from the underlying store and the view.
        """
        if f.id in self._store:
            del self._store[f.id]
            if f in self._view:
                self._view.remove(f)
                self.sig_remove.send(self, flow=f)

    def update(self, f: mitmproxy.flow.Flow):
        """
            Updates a flow. If the flow is not in the state, it's ignored.
        """
        if f.id in self._store:
            if self.filter(f):
                if f not in self._view:
                    self._view.add(f)
                    self.sig_add.send(self, flow=f)
                else:
                    self.sig_update.send(self, flow=f)
            else:
                try:
                    self._view.remove(f)
                    self.sig_remove.send(self, flow=f)
                except ValueError:
                    # The value was not in the view
                    pass

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
                self.set_order(key_request_start)
            else:
                for _, name, func in orders:
                    if name == opts.order:
                        self.set_order(func)
                        break
                else:
                    raise exceptions.OptionsError(
                        "Unknown flow order: %s" % opts.order
                    )
        if "order_reversed" in updated:
            self.set_reversed(opts.order_reversed)

    def request(self, f):
        self.add(f)

    def intercept(self, f):
        self.update(f)

    def resume(self, f):
        self.update(f)

    def error(self, f):
        self.update(f)

    def response(self, f):
        self.update(f)


class Focus:
    """
        Tracks a focus element within a View.
    """
    def __init__(self, v: View) -> None:
        self.view = v
        self._flow = None
        self.sig_change = blinker.Signal()
        if len(self.view):
            self.flow = self.view[0]
        v.sig_add.connect(self._sig_add)
        v.sig_remove.connect(self._sig_remove)
        v.sig_refresh.connect(self._sig_refresh)

    @property
    def flow(self) -> typing.Optional[mitmproxy.flow.Flow]:
        return self._flow

    @flow.setter
    def flow(self, f: mitmproxy.flow.Flow):
        if f is not None and f not in self.view:
            raise ValueError("Attempt to set focus to flow not in view")
        self._flow = f
        self.sig_change.send(self)

    @property
    def index(self) -> typing.Optional[int]:
        if self.flow:
            return self.view.index(self.flow)

    @index.setter
    def index(self, idx) -> typing.Optional[int]:
        if idx < 0 or idx > len(self.view) - 1:
            raise ValueError("Index out of view bounds")
        self.flow = self.view[idx]

    def _nearest(self, f, v):
        return min(v.bisect(f), len(v) - 1)

    def _sig_remove(self, view, flow):
        if len(view) == 0:
            self.flow = None
        elif flow is self.flow:
            self.flow = view[self._nearest(self.flow, view)]

    def _sig_refresh(self, view):
        if len(view) == 0:
            self.flow = None
        elif self.flow is None:
            self.flow = view[0]
        elif self.flow not in view:
            self.flow = view[self._nearest(self.flow, view)]

    def _sig_add(self, view, flow):
        # We only have to act if we don't have a focus element
        if not self.flow:
            self.flow = flow


class Settings(collections.Mapping):
    def __init__(self, view: View) -> None:
        self.view = view
        self.values = {}
        view.sig_remove.connect(self._sig_remove)
        view.sig_refresh.connect(self._sig_refresh)

    def __iter__(self) -> typing.Iterable:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, f: mitmproxy.flow.Flow) -> dict:
        if f.id not in self.view._store:
            raise KeyError
        return self.values.setdefault(f.id, {})

    def _sig_remove(self, view, flow):
        if flow.id in self.values:
            del self.values[flow.id]

    def _sig_refresh(self, view):
        for fid in self.values.keys():
            if fid not in view._store:
                del self.values[fid]
