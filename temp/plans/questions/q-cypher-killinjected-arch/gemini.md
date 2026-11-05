
### Voice 1: The Protocol-Mirror
- **Q1 (per-protocol vs generic):** [A] — Consistency with `MessageInjected` ensures familiar patterns for existing protocol layers.
- **Q2 (emission point):** [C] — Mirrors `inject.tcp/udp` by placing the event emission in the `proxyserver` addon.
- **Q3 (mid-upgrade ownership):** Protocol-specific subclasses (e.g., `WebSocketKillInjected`) provide unambiguous routing to the current active layer.
- **Q4 (scope vs #5484):** [Yes] — Allows `HttpLayer` to catch the signal during active response body streaming.

### Voice 2: The Pragmatist
- **Q1 (per-protocol vs generic):** [B] — Subclasses are unnecessary as "kill" has no protocol-specific payload variance.
- **Q2 (emission point):** [B] — Emit from `core.py:flow.kill` command to keep "action + signal" logic centralized.
- **Q3 (mid-upgrade ownership):** Generic event propagates until the first layer capable of closing the flow (usually the leaf) handles it.
- **Q4 (scope vs #5484):** [Yes] — Breaking out of `yield from self.event_to_child` loops in `HttpLayer` solves this.

### Voice 3: The Architect
- **Q1 (per-protocol vs generic):** [B] — Keeps the event system lean; generic `KillInjected(flow)` is sufficient for all layers.
- **Q2 (emission point):** [C] — `proxyserver` should own event injection; `Flow` must remain a pure data class.
- **Q3 (mid-upgrade ownership):** The event is routed to the `ConnectionHandler` for the flow's client connection and handled by the current layer.
- **Q4 (scope vs #5484):** [Yes] — Stream termination becomes a standard event-handling case in the HTTP layer.

### OVERALL VERDICT:
Implement a single generic `KillInjected(flow: Flow)` event in `mitmproxy/proxy/events.py`. While `MessageInjected` uses subclasses for payload typing, `KillInjected` lacks this requirement, making a generic event cleaner and more idiomatic for lifecycle signaling. The event should be emitted via a new `inject.kill` command (or an update to `inject_event`) in `mitmproxy/addons/proxyserver.py`, keeping the `Flow` class decoupled from the proxy's event loop. This design naturally closes #5484 as it provides the necessary signal for `HttpLayer` to terminate response streaming mid-transit.

