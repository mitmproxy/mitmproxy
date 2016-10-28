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

from mitmproxy import flow
from mitmproxy import flowfilter


def key_request_start(f: flow.Flow) -> datetime.datetime:
    return f.request.timestamp_start or 0


def key_request_method(f: flow.Flow) -> str:
    return f.request.method


matchall = flowfilter.parse(".")


class View(collections.Sequence):
    def __init__(self):
        super().__init__()
        self._store = {}
        self.filter = matchall
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

    def __getitem__(self, offset) -> flow.Flow:
        return self._view[self._rev(offset)]

    # Reflect some methods to the efficient underlying implementation

    def bisect(self, f: flow.Flow) -> int:
        v = self._view.bisect(f)
        # Bisect returns an item to the RIGHT of the existing entries.
        if v == 0:
            return v
        return self._rev(v - 1) + 1

    def index(self, f: flow.Flow) -> int:
        return self._rev(self._view.index(f))

    # API

    def toggle_reversed(self):
        self.order_reversed = not self.order_reversed
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
        self._view.clear()
        for i in self._store.values():
            if self.filter(i):
                self._view.add(i)
        self.sig_refresh.send(self)

    def clear(self):
        """
            Clears both the state and view.
        """
        self._state.clear()
        self._view.clear()
        self.sig_refresh.send(self)

    def add(self, f: flow.Flow):
        """
            Adds a flow to the state. If the flow already exists, it is
            ignored.
        """
        if f.id not in self._store:
            self._store[f.id] = f
            if self.filter(f):
                self._view.add(f)
                self.sig_add.send(self, flow=f)

    def remove(self, f: flow.Flow):
        """
            Removes the flow from the underlying store and the view.
        """
        if f.id in self._store:
            del self._store[f.id]
            if f in self._view:
                self._view.remove(f)
                self.sig_remove.send(self, flow=f)

    def update(self, f: flow.Flow):
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
        self._focusflow = None
        if len(self.view):
            self.focusflow = self.view[0]
        v.sig_add.connect(self._sig_add)
        v.sig_remove.connect(self._sig_remove)
        v.sig_refresh.connect(self._sig_refresh)

    @property
    def focusflow(self) -> typing.Optional[flow.Flow]:
        return self._focusflow

    @focusflow.setter
    def focusflow(self, f: flow.Flow):
        if f is not None and f not in self.view:
            raise ValueError("Attempt to set focus to flow not in view")
        self._focusflow = f

    @property
    def index(self) -> typing.Optional[int]:
        if self.focusflow:
            return self.view.index(self.focusflow)

    def next(self):
        """
            Sets the focus to the next flow.
        """
        if self.focusflow:
            idx = min(self.index + 1, len(self.view) - 1)
            self.focusflow = self.view[idx]

    def prev(self):
        """
            Sets the focus to the previous flow.
        """
        if self.focusflow:
            idx = max(self.index - 1, 0)
            self.focusflow = self.view[idx]

    def _nearest(self, f, v):
        return min(v.bisect(f), len(v) - 1)

    def _sig_remove(self, view, flow):
        if len(view) == 0:
            self.focusflow = None
        elif flow is self.focusflow:
            self.focusflow = view[self._nearest(self.focusflow, view)]

    def _sig_refresh(self, view):
        if len(view) == 0:
            self.focusflow = None
        elif self.focusflow is None:
            self.focusflow = view[0]
        elif self.focusflow not in view:
            self.focusflow = view[self._nearest(self.focusflow, view)]

    def _sig_add(self, view, flow):
        # We only have to act if we don't have a focus element
        if not self.focusflow:
            self.focusflow = flow


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

    def __getitem__(self, f: flow.Flow) -> dict:
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
