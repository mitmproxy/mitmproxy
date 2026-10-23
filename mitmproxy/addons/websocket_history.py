"""Discard unused WebSocket history in mitmdump."""

import weakref

from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy.addonmanager import Loader

HISTORY_OPTIONS = {
    "keep_websocket_messages",
    "save_stream_file",
    "hardump",
    # Body filters can match messages received earlier in the connection.
    "dumper_filter",
}


class WebSocketHistory:
    def __init__(self) -> None:
        # Track connections without owning their lifetime or their messages.
        self._unrecorded_flows: weakref.WeakSet[http.HTTPFlow] = weakref.WeakSet()

    def load(self, loader: Loader) -> None:
        loader.add_option(
            "keep_websocket_messages",
            bool,
            False,
            "Retain WebSocket message history in mitmdump for addons that need "
            "earlier messages. History is always retained when writing flow or "
            "HAR files, or using a dumper filter. Otherwise messages are discarded "
            "after hooks and forwarding. Retaining history can use unbounded "
            "memory on long-lived connections. Configure this before connecting.",
        )

    def _requires_history(self) -> bool:
        # The dumper is optional when embedding DumpMaster.
        return any(getattr(ctx.options, name, False) for name in HISTORY_OPTIONS)

    def configure(self, updated: set[str]) -> None:
        if (
            updated & HISTORY_OPTIONS
            and self._requires_history()
            and any(flow.live for flow in self._unrecorded_flows)
        ):
            # The protocol layer marks the flow non-live after *all* end hooks.
            # A close timestamp or an update event can arrive before Save runs.
            raise exceptions.OptionsError(
                "Cannot enable WebSocket history while connections started "
                "without recording are active. Close these connections before "
                "enabling recording, a dumper filter, or keep_websocket_messages."
            )

    def websocket_start(self, flow: http.HTTPFlow) -> None:
        if not flow.live:
            return  # Reading a saved flow must preserve its recorded messages.
        assert flow.websocket is not None
        flow.websocket.store_messages = self._requires_history()
        if not flow.websocket.store_messages:
            self._unrecorded_flows.add(flow)
