"""
The View:

- Keeps track of a store of viewitems
- Maintains a filtered, ordered view onto that list of viewitems
- Exposes a number of signals so the view can be monitored
- Tracks focus within the view
- Exposes a settings store for viewitems that automatically expires if the viewitem is
  removed from the store.
"""
import collections
import typing
import re

import blinker
import sortedcontainers

import mitmproxy.viewitem
from mitmproxy import flowfilter
from mitmproxy import exceptions
from mitmproxy import ctx
from mitmproxy import io
from mitmproxy import viewitem  # noqa

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

    def generate(self, i: viewitem.ViewItem) -> typing.Any:  # pragma: no cover
        pass

    def refresh(self, i):
        k = self._key()
        old = self.view.settings[i][k]
        new = self.generate(i)
        if old != new:
            self.view._view.remove(i)
            self.view.settings[i][k] = new
            self.view._view.add(i)
            self.view.sig_view_refresh.send(self.view)

    def _key(self):
        return "_order_%s" % id(self)

    def __call__(self, i):
        if i.id in self.view._store:
            k = self._key()
            s = self.view.settings[i]
            if k in s:
                return s[k]
            val = self.generate(i)
            s[k] = val
            return val
        else:
            return self.generate(i)


class OrderTimestamp(_OrderKey):
    def generate(self, i: viewitem.ViewItem) -> int:
        raise NotImplementedError()


class OrderKeySize(_OrderKey):
    def generate(self, i: viewitem.ViewItem) -> int:
        raise NotImplementedError()


class View(collections.abc.Sequence):
    def __init__(self):
        super().__init__()
        self.matchall = None
        self.base_orders = [
            ("t", "time"),
        ]

        self._store = collections.OrderedDict()
        self.filter = self.matchall
        # This used to store the specific filter for the view with a other filter than the main filter
        # key: the name of the filter
        # value: the specific filter corresponding to the name
        # Note that all other attributes named "filtred_views..." are generally used for this features
        # All of theses attributes are a dic() with the same keys
        self.filtred_views_filter = {}
        # Should we show only marked flows?
        self.show_marked = False

        self.default_order = OrderTimestamp(self)
        self.orders = dict(time = OrderTimestamp(self))
        self.order_key = self.default_order
        self.order_reversed = False
        self.focus_follow = False

        self._view = sortedcontainers.SortedListWithKey(
            key = self.order_key
        )
        # This used to store a list of items with a other filter than the main filter
        # key: the name of the filter
        # value: the same list than "_view" but with an other filter
        self.filtred_views: dict[str, sortedcontainer.SortedListWithKey] = {}

        # The sig_view* signals broadcast events that affect the view. That is,
        # an update to a flow in the store but not in the view does not trigger
        # a signal. All signals are called after the view has been updated.
        self.sig_view_update = blinker.Signal()
        self.sig_view_add = blinker.Signal()
        self.filtred_views_sig_view_add = {}
        self.sig_view_remove = blinker.Signal()
        self.filtred_views_sig_view_remove = {}
        # Signals that the view should be refreshed completely
        self.sig_view_refresh = blinker.Signal()
        self.filtred_views_sig_view_refresh = {}

        # The sig_store* signals broadcast events that affect the underlying
        # store. If a flow is removed from just the view, sig_view_remove is
        # triggered. If it is removed from the store while it is also in the
        # view, both sig_store_remove and sig_view_remove are triggered.
        self.sig_store_remove = blinker.Signal()
        # Signals that the store should be refreshed completely
        self.sig_store_refresh = blinker.Signal()

        self.focus = Focus(self)
        self.filtred_views_focus = {}
        self.settings = Settings(self)

    def load(self, loader):
        loader.add_option(
            "view_filter_%s" % self.flow_type, typing.Optional[str], None,
            "Limit the view to matching flows."
        )
        loader.add_option(
            "view_order_%s" % self.flow_type, str, "time",
            "Flow sort order.",
            choices=list(map(lambda c: c[1], self.base_orders)),
        )
        loader.add_option(
            "view_order_reversed", bool, False,
            "Reverse the sorting order."
        )
        loader.add_option(
            "console_focus_follow", bool, False,
            "Focus follows new flows."
        )

    @property
    def flow_type(self) -> str:
        """
        Used to specify the flow type which is contained in this view
        Need to be specified in subclass
        """
        raise NotImplementedError()

    def store_count(self):
        return len(self._store)

    def _rev(self, idx: int, view_name=None) -> int:
        """
            Reverses an index, if needed
        """
        if self.order_reversed:
            if idx < 0:
                idx = -idx - 1
            else:
                if view_name:
                    idx = len(self.filtred_views[view_name]) - idx - 1
                else:
                    idx = len(self._view) - idx - 1
                if idx < 0:
                    raise IndexError
        return idx

    def __len__(self):
        return len(self._view)

    def __getitem__(self, offset) -> typing.Any:
        return self._view[self._rev(offset)]

    # Reflect some methods to the efficient underlying implementation

    def _bisect(self, i: mitmproxy.viewitem.ViewItem, view_name=None) -> int:
        if view_name:
            v = self.filtred_views[view_name].bisect_right(i)
        else:
            v = self._view.bisect_right(i)
        return self._rev(v - 1, view_name) + 1

    def index(self, i: mitmproxy.viewitem.ViewItem,
              start: int = 0, stop: typing.Optional[int] = None,
              view_name: typing.Sequence[str] = None) -> int:
        if view_name:
            return self._rev(self.filtred_views[view_name].index(i, start, stop), view_name)
        else:
            return self._rev(self._view.index(i, start, stop))

    def __contains__(self, i: typing.Any, view_name: typing.Sequence[str] = None) -> bool:
        if view_name:
            return self._view[view_name].__contains__(i)
        else:
            return self._view.__contains__(i)

    def _order_key_name(self):
        return "_order_%s" % id(self.order_key)

    def _base_add(self, i, view_name=None):
        self.settings[i][self._order_key_name()] = self.order_key(i)
        if view_name:
            self.filtred_views[view_name].add(i)
        else:
            self._view.add(i)

    def _refilter(self):
        for view in [self._view, *self.filtred_views.values()]:
            view.clear()
        for i in self._store.values():
            if self.show_marked and not i.marked:
                continue
            if self.filter(i):
                self._base_add(i)
            for name, flt in self.filtred_views_filter.items():
                if flt(i):
                    self._base_add(i, name)
        self.sig_view_refresh.send(self)
        for name, signal in self.filtred_views_sig_view_refresh.items():
            signal.send(self.filtred_views[name])

    """ View API """

    # Focus
    def go(self, dst: int) -> None:
        """
            Go to a specified offset. Positive offests are from the beginning of
            the view, negative from the end of the view, so that 0 is the first
            item, -1 is the last item.
        """
        if len(self) == 0:
            return
        if dst < 0:
            dst = len(self) + dst
        if dst < 0:
            dst = 0
        if dst > len(self) - 1:
            dst = len(self) - 1
        self.focus.item = self[dst]

    def focus_next(self) -> None:
        """
            Set focus to the next item.
        """
        idx = self.focus.index + 1
        if self.inbounds(idx):
            self.focus.item = self[idx]

    def focus_prev(self) -> None:
        """
            Set focus to the previous flow.
        """
        idx = self.focus.index - 1
        if self.inbounds(idx):
            self.focus.item = self[idx]

    # Order
    def order_options(self) -> typing.Sequence[str]:
        """
            Choices supported by the view_order option.
        """
        return list(sorted(self.orders.keys()))

    def set_reversed(self, value: bool) -> None:
        self.order_reversed = value
        self.sig_view_refresh.send(self)
        for name, signal in self.filtred_views_sig_view_refresh.items():
            signal.send(self.filtred_views[name])

    def set_order(self, order: str) -> None:
        """
            Sets the current view order.
        """
        if order not in self.orders:
            raise exceptions.CommandError(
                "Unknown item order: %s" % order
            )
        order_key = self.orders[order]
        self.order_key = order_key
        newview = sortedcontainers.SortedListWithKey(key=order_key)
        newview.update(self._view)
        self._view = newview

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
    def set_filter_cmd(self, i: str) -> None:
        """
            Sets the current view filter.
        """
        filt = None
        if i:
            filt = flowfilter.parse(i)
            if not filt:
                raise exceptions.CommandError(
                    "Invalid interception filter: %s" % i
                )
        self.set_filter(filt)

    def set_filter(self, flt: typing.Optional[flowfilter.TFilter], view_name: typing.Sequence[str] = None):
        if not view_name:
            self.filter = flt or self.matchall
        else:
            self.filtred_views[view_name] = self._view.copy()
            self.filtred_views_filter[view_name] = flt or self.matchall
            self.filtred_views_sig_view_add[view_name] = blinker.Signal()
            self.filtred_views_sig_view_remove[view_name] = blinker.Signal()
            self.filtred_views_sig_view_refresh[view_name] = blinker.Signal()
            self.filtred_views_focus[view_name] = Focus(self, view_name)
        self._refilter()

    def add_filtred_view(self, i: str, name: str) -> None:
        filt = None
        if i:
            filt = flowfilter.parse(i)
            if not filt:
                raise exceptions.CommandError(
                    "Invalid interception filter: %s" % i
                )
        self.set_filter(filt, name)

    # View Updates
    def clear(self) -> None:
        """
            Clears both the store and view.
        """
        self._store.clear()
        self._view.clear()
        self.sig_view_refresh.send(self)
        self.sig_store_refresh.send(self)
        for name, signal in self.filtred_views_sig_view_refresh.items():
            signal.send(self.filtred_views[name])

    def clear_not_marked(self) -> None:
        """
            Clears only the unmarked viewitem.
        """
        for viewitem in self._store.copy().values():
            if not viewitem.marked:
                self._store.pop(viewitem.id)

        self._refilter()
        self.sig_store_refresh.send(self)

    # View Settings
    def getvalue(self, i: mitmproxy.viewitem.ViewItem, key: str, default: str) -> str:
        """
            Get a value from the settings store for the specified viewitem.
        """
        return self.settings[i].get(key, default)

    def setvalue_toggle(
        self,
        viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem],
        key: str
    ) -> None:
        """
            Toggle a boolean value in the settings store, setting the value to
            the string "true" or "false".
        """
        updated = []
        for i in viewitems:
            current = self.settings[i].get("key", "false")
            self.settings[i][key] = "false" if current == "true" else "true"
            updated.append(i)
        ctx.master.addons.trigger("update", updated)

    def setvalue(
        self,
        viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem],
        key: str, value: str
    ) -> None:
        """
            Set a value in the settings store for the specified viewitems.
        """
        updated = []
        for i in viewitems:
            self.settings[i][key] = value
            updated.append(i)
        ctx.master.addons.trigger("update", updated)

    # Flows
    def duplicate(self, viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Duplicates the specified viewitems, and sets the focus to the first
            duplicate.
        """
        dups = [i.copy() for i in viewitems]
        if dups:
            self.add(dups)
            self.focus.item = dups[0]
            ctx.log.alert("Duplicated %s viewitems" % len(dups))

    def remove(self, viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Removes the flow from the underlying store and the view.
        """
        for i in viewitems:
            if i.id in self._store:
                if i.flow.killable:
                    i.flow.kill()
                if i in self._view:
                    # We manually pass the index here because multiple viewitems may have the same
                    # sorting key, and we cannot reconstruct the index from that.
                    idx = self._view.index(i)
                    self._view.remove(i)
                    self.sig_view_remove.send(self, item=i, index=idx)
                for name in self.filtred_views.keys():
                    if i in self.filtred_views[name]:
                        idx = self.filtred_views[name].index(i)
                        self.filtred_views[name].remove(i)
                        self.filtred_views_sig_view_remove[name].send(self.filtred_views[name], item=i, index=idx)
                del self._store[i.id]
                self.sig_store_remove.send(self, item=i)
        if len(viewitems) > 1:
            ctx.log.alert("Removed %s viewitems" % len(viewitems))

    def resolve(self, spec: str) -> typing.Sequence[mitmproxy.viewitem.ViewItem]:
        """
            Resolve a viewitem list specification to an actual list of viewitems.
        """
        view_name = None
        if re.match(r'@\w+\.\w+\.\w+', spec):
            spec, view_name = re.match(r'(@\w+)\.\w+\.(\w+)', spec).group(1, 2)
        if re.match(r'@\w+\.\w+', spec):
            spec = re.match(r'(@\w+)\.\w+', spec).group(0)

        if spec == "@all":
            return [i for i in self._store.values()]
        if spec == "@focus":
            if view_name:
                return [self.filtred_views_focus[view_name].item] if self.filtred_views_focus[view_name].item else []
            else:
                return [self.focus.item] if self.focus.item else []
        elif spec == "@shown":
            if view_name:
                return [i for i in self.filtred_views[view_name]]
            else:
                return [i for i in self]
        elif spec == "@hidden":
            if view_name:
                return [i for i in self._store.values() if i not in self.filtred_views[view_name]]
            else:
                return [i for i in self._store.values() if i not in self._view]
        elif spec == "@marked":
            return [i for i in self._store.values() if i.marked]
        elif spec == "@unmarked":
            return [i for i in self._store.values() if not i.marked]
        else:
            filt = flowfilter.parse(spec)
            if not filt:
                raise exceptions.CommandError("Invalid flow filter: %s" % spec)
            return [i for i in self._store.values() if filt(i)]

    def load_file(self, path: mitmproxy.types.Path) -> None:
        """
            Load viewitem into the view, without processing them with addons.
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

    def add(self, viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Adds a flow to the state. If the flow already exists, it is
            ignored.
        """
        for i in viewitems:
            if i.id not in self._store:
                self._store[i.id] = i
                if self.filter(i):
                    self._base_add(i)
                    if self.focus_follow:
                        self.focus.item = i
                    self.sig_view_add.send(self, item=i)
                for name, flt in self.filtred_views_filter.items():
                    if flt(i):
                        self._base_add(i, name)
                        if self.focus_follow:
                            self.filtred_views_focus[name].viewitem = i
                        self.filtred_views_sig_view_add[name].send(self, item=i)

    def get_by_id(self, flow_id: str) -> typing.Optional[mitmproxy.viewitem.ViewItem]:
        """
            Get flow with the given id from the store.
            Returns None if the flow is not found.
        """
        return self._store.get(flow_id)

    # View Properties
    def get_length(self) -> int:
        """
            Returns view length.
        """
        return len(self)

    def get_marked(self) -> bool:
        """
            Returns true if view is in marked mode.
        """
        return self.show_marked

    def toggle_marked(self) -> None:
        """
            Toggle whether to show marked views only.
        """
        self.show_marked = not self.show_marked
        self._refilter()

    def inbounds(self, index: int, name: str = None) -> bool:
        """
            Is this 0 <= index < len(self)?
        """
        if name and name != "None":
            return 0 <= index < len(self.filtred_views[name])
        else:
            return 0 <= index < len(self)

    # Event handlers
    def configure(self, updated):
        if "view_filter_%s" % self.flow_type in updated:
            filt = None
            view_filter = getattr(ctx.options, "view_filter_%s" % self.flow_type)
            if view_filter:
                filt = flowfilter.parse(view_filter)
                if not filt:
                    raise exceptions.OptionsError(
                        "Invalid interception filter: %s" % view_filter
                    )
            self.set_filter(filt)
        if "view_order_%s" % self.flow_type in updated:
            view_order = getattr(ctx.options, "view_order_%s" % self.flow_type)
            if view_order not in self.orders:
                raise exceptions.OptionsError(
                    "Unknown flow order: %s" % view_order
                )
            self.set_order(view_order)
        if "view_order_reversed" in updated:
            self.set_reversed(ctx.options.view_order_reversed)
        if "console_focus_follow" in updated:
            self.focus_follow = ctx.options.console_focus_follow

    def intercept(self, i):
        self.update([i])

    def resume(self, i):
        self.update([i])

    def update(self, viewitems: typing.Sequence[mitmproxy.viewitem.ViewItem]) -> None:
        """
            Updates a list of viewitems. If flow is not in the state, it's ignored.
        """
        for i in viewitems:
            if i.id in self._store:
                if self.filter(i):
                    if i not in self._view:
                        self._base_add(i)
                        if self.focus_follow:
                            self.focus.item = i
                        self.sig_view_add.send(self, item=i)
                    else:
                        # This is a tad complicated. The sortedcontainers
                        # implementation assumes that the order key is stable. If
                        # it changes mid-way Very Bad Things happen. We detect when
                        # this happens, and re-fresh the item.
                        self.order_key.refresh(i)
                        self.sig_view_update.send(self, item=i)
                else:
                    try:
                        idx = self._view.index(i)
                    except ValueError:
                        pass  # The value was not in the view
                    else:
                        self._view.remove(i)
                        self.sig_view_remove.send(self, item=i, index=idx)

                for name, flt in self.filtred_views_filter.items():
                    if flt(i):
                        if i not in self._view:
                            self._base_add(i, name)
                            if self.focus_follow:
                                self.focus.item = i
                            self.filtred_views_sig_view_add[name].send(self, item=i)
                        else:
                            # This is a tad complicated. The sortedcontainers
                            # implementation assumes that the order key is stable. If
                            # it changes mid-way Very Bad Things happen. We detect when
                            # this happens, and re-fresh the item.
                            self.order_key.refresh(i)
                            self.sig_view_update.send(self, item=i)
                    else:
                        try:
                            idx = self._view.index(i)
                        except ValueError:
                            pass  # The value was not in the view
                        else:
                            self._view.remove(i)
                            self.filtred_views_sig_view_remove[name].send(self, item=i, index=idx)


class Focus:
    """
        Tracks a focus element within a View.
    """

    def __init__(self, v: View, view_name=None) -> None:
        self.base_view, self.view_name = v, view_name
        if view_name:
            self.view = v.filtred_views[view_name]
        else:
            self.view = v
        self._item: mitmproxy.viewitem.ViewItem = None
        self.sig_change = blinker.Signal()
        if len(self.view):
            self.item = self.view[0]
        if view_name:
            v.filtred_views_sig_view_add[view_name].connect(self._sig_view_add)
            v.filtred_views_sig_view_remove[view_name].connect(self._sig_view_remove)
            v.filtred_views_sig_view_refresh[view_name].connect(self._sig_view_refresh)
        else:
            v.sig_view_add.connect(self._sig_view_add)
            v.sig_view_remove.connect(self._sig_view_remove)
            v.sig_view_refresh.connect(self._sig_view_refresh)

    @property
    def item(self) -> typing.Optional[mitmproxy.viewitem.ViewItem]:
        return self._item

    @item.setter
    def item(self, i: typing.Optional[mitmproxy.viewitem.ViewItem]):
        if i is not None and i not in self.view:
            raise ValueError("Attempt to set focus to item not in view")
        self._item = i
        self.sig_change.send(self)

    @property
    def index(self) -> typing.Optional[int]:
        if self.item:
            return self.view.index(self.item)
        return None

    @index.setter
    def index(self, idx):
        if idx < 0 or idx > len(self.view) - 1:
            raise ValueError("Index out of viewitem bounds")
        self.item = self.view[idx]

    def _nearest(self, i, v):
        return min(self.base_view._bisect(i, self.view_name), len(v) - 1)

    def _sig_view_remove(self, view, item, index):
        if len(view) == 0:
            self.item = None
        elif item is self.item:
            self.index = min(index, len(self.view) - 1)

    def _sig_view_refresh(self, view):
        if len(view) == 0:
            self.item = None
        elif self.item is None:
            self.item = view[0]
        elif self.item not in view:
            self.item = view[self._nearest(self.item, view)]

    def _sig_view_add(self, view, item):
        # We only have to act if we don't have a focus element
        if not self.item:
            self.item = item


class Settings(collections.abc.Mapping):
    def __init__(self, view: View) -> None:
        self.view = view
        self._values: typing.MutableMapping[str, typing.Dict] = {}
        view.sig_store_remove.connect(self._sig_store_remove)
        view.sig_store_refresh.connect(self._sig_store_refresh)

    def __iter__(self) -> typing.Iterator:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __getitem__(self, i: mitmproxy.viewitem.ViewItem) -> dict:
        if i.id not in self.view._store:
            raise KeyError
        return self._values.setdefault(i.id, {})

    def _sig_store_remove(self, view, item):
        if item.id in self._values:
            del self._values[item.id]

    def _sig_store_refresh(self, view):
        for fid in list(self._values.keys()):
            if fid not in view._store:
                del self._values[fid]
