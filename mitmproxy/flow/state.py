from __future__ import absolute_import, print_function, division

from abc import abstractmethod, ABCMeta

import six
from typing import List  # noqa

from mitmproxy import filt
from mitmproxy import models  # noqa


@six.add_metaclass(ABCMeta)
class FlowList(object):
    def __init__(self):
        self._list = []  # type: List[models.Flow]

    def __iter__(self):
        return iter(self._list)

    def __contains__(self, item):
        return item in self._list

    def __getitem__(self, item):
        return self._list[item]

    def __bool__(self):
        return bool(self._list)

    if six.PY2:
        __nonzero__ = __bool__

    def __len__(self):
        return len(self._list)

    def index(self, f):
        return self._list.index(f)

    @abstractmethod
    def _add(self, f):
        return

    @abstractmethod
    def _update(self, f):
        return

    @abstractmethod
    def _remove(self, f):
        return


def _pos(*args):
    return True


class FlowView(FlowList):
    def __init__(self, store, filt=None):
        super(FlowView, self).__init__()
        if not filt:
            filt = _pos
        self._build(store, filt)

        self.store = store
        self.store.views.append(self)

    def _close(self):
        self.store.views.remove(self)

    def _build(self, flows, filt=None):
        if filt:
            self.filt = filt
        self._list = list(filter(self.filt, flows))

    def _add(self, f):
        if self.filt(f):
            self._list.append(f)

    def _update(self, f):
        if f not in self._list:
            self._add(f)
        elif not self.filt(f):
            self._remove(f)

    def _remove(self, f):
        if f in self._list:
            self._list.remove(f)

    def _recalculate(self, flows):
        self._build(flows)


class FlowStore(FlowList):
    """
    Responsible for handling flows in the state:
    Keeps a list of all flows and provides views on them.
    """

    def __init__(self):
        super(FlowStore, self).__init__()
        self._set = set()  # Used for O(1) lookups
        self.views = []
        self._recalculate_views()

    def get(self, flow_id):
        for f in self._list:
            if f.id == flow_id:
                return f

    def __contains__(self, f):
        return f in self._set

    def _add(self, f):
        """
        Adds a flow to the state.
        The flow to add must not be present in the state.
        """
        self._list.append(f)
        self._set.add(f)
        for view in self.views:
            view._add(f)

    def _update(self, f):
        """
        Notifies the state that a flow has been updated.
        The flow must be present in the state.
        """
        if f in self:
            for view in self.views:
                view._update(f)

    def _remove(self, f):
        """
        Deletes a flow from the state.
        The flow must be present in the state.
        """
        self._list.remove(f)
        self._set.remove(f)
        for view in self.views:
            view._remove(f)

    # Expensive bulk operations

    def _extend(self, flows):
        """
        Adds a list of flows to the state.
        The list of flows to add must not contain flows that are already in the state.
        """
        self._list.extend(flows)
        self._set.update(flows)
        self._recalculate_views()

    def _clear(self):
        self._list = []
        self._set = set()
        self._recalculate_views()

    def _recalculate_views(self):
        """
        Expensive operation: Recalculate all the views after a bulk change.
        """
        for view in self.views:
            view._recalculate(self)

    # Utility functions.
    # There are some common cases where we need to argue about all flows
    # irrespective of filters on the view etc (i.e. on shutdown).

    def active_count(self):
        c = 0
        for i in self._list:
            if not i.response and not i.error:
                c += 1
        return c

    # TODO: Should accept_all operate on views or on all flows?
    def accept_all(self, master):
        for f in self._list:
            f.accept_intercept(master)

    def kill_all(self, master):
        for f in self._list:
            if f.killable:
                f.kill(master)


class State(object):
    def __init__(self):
        self.flows = FlowStore()
        self.view = FlowView(self.flows, None)

        # These are compiled filt expressions:
        self.intercept = None

    @property
    def filter_txt(self):
        return getattr(self.view.filt, "pattern", None)

    def flow_count(self):
        return len(self.flows)

    # TODO: All functions regarding flows that don't cause side-effects should
    # be moved into FlowStore.
    def index(self, f):
        return self.flows.index(f)

    def active_flow_count(self):
        return self.flows.active_count()

    def add_flow(self, f):
        """
            Add a request to the state.
        """
        self.flows._add(f)
        return f

    def update_flow(self, f):
        """
            Add a response to the state.
        """
        self.flows._update(f)
        return f

    def delete_flow(self, f):
        self.flows._remove(f)

    def load_flows(self, flows):
        self.flows._extend(flows)

    def set_view_filter(self, txt):
        if txt == self.filter_txt:
            return
        if txt:
            f = filt.parse(txt)
            if not f:
                return "Invalid filter expression."
            self.view._close()
            self.view = FlowView(self.flows, f)
        else:
            self.view._close()
            self.view = FlowView(self.flows, None)

    def set_intercept(self, txt):
        if txt:
            f = filt.parse(txt)
            if not f:
                return "Invalid filter expression."
            self.intercept = f
        else:
            self.intercept = None

    @property
    def intercept_txt(self):
        return getattr(self.intercept, "pattern", None)

    def clear(self):
        self.flows._clear()

    def accept_all(self, master):
        self.flows.accept_all(master)

    def backup(self, f):
        f.backup()
        self.update_flow(f)

    def revert(self, f):
        f.revert()
        self.update_flow(f)

    def killall(self, master):
        self.flows.kill_all(master)
