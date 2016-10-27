"""
The View:

- Keeps track of a store of flows
- Maintains a filtered, ordered view onto that list of flows
- Exposes various operations on flows in the store - notably intercept and
  resume
- Exposes a number of signals so the view can be monitored
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
        self.order_reverse = False
        self._view = sortedcontainers.SortedListWithKey(key = self.order_key)

        # These signals broadcast events that affect the view. That is, an
        # update to a flow in the store but not in the view does not trigger a
        # signal. All signals are called after the view has been updated.
        self.sig_update = blinker.Signal()
        self.sig_add = blinker.Signal()
        self.sig_remove = blinker.Signal()
        # Signals that the view should be refreshed completely
        self.sig_refresh = blinker.Signal()

    def __len__(self):
        return len(self._view)

    def __getitem__(self, offset) -> flow.Flow:
        if self.order_reverse:
            offset = -offset - 1
        return self._view[offset]

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
