
**Q1 (per-protocol vs generic):** B — cleaner, no-payload lifecycle event; boilerplate avoided.

**Q2 (emission point):** B — addon path mirrors inject_message exactly; Flow stays pure data class.

**Q3 (mid-upgrade ownership):** Lowest common layer (TCP/HTTP base) owns it; event routes to current handler via flow.client_conn.id regardless of upgrade state. For per-protocol, inject_event would normalize to base KillInjected during CONNECT/WebSocket pending.

**Q4 (scope vs #5484):** Yes — injecting the event into the live layer stack forces immediate close/teardown even for intercepted flows where TUI `x` previously did nothing.

**OVERALL VERDICT:** Implement single `KillInjected(Event)` (Q1=B) emitted from the `flow.kill` command handler in core.py after calling `f.kill()` (Q2=B). `proxyserver.inject_event` routes it to the active connection handler by client_conn.id, which treats it like any other kill signal in its layer (closing connections, cleaning up in-transit flows). This mirrors MessageInjected injection path without polluting Flow, cleanly resolves both #4711 (in-transit) and #5484 (intercepted), and keeps layering intact for maintainer's review.

