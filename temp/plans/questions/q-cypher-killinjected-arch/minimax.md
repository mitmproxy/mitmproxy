## Cypher Verdict: KillInjected Implementation

**Q1 (per-protocol vs generic):** B (generic) — `MessageInjected[T]` subclasses exist because each protocol bundles a typed payload (`TCPMessage`, `UDPMessage`, `WebSocketMessage`). `KillInjected` has no payload — it's a lifecycle signal. Per-protocol subclasses would be documentation Lies that imply payload differentiation where none exists. A single `KillInjected(Event)` is honest and requires zero new typing infrastructure.

**Q2 (emission point):** B (from `core.py:flow.kill` command) — The addon command is the proper emission point. `Flow.kill()` stays a pure state mutation (sets `error`, `live = False`, clears `intercepted`, fires `_resume_event`). The addon command then calls `proxyserver.inject_event(KillInjected(flow))`, which routes to the live connection's layer stack. This is the exact mirror of how `inject.tcp`/`inject.udp`/`inject.websocket` work — addon validates, creates event, injects. Changing `Flow.kill()` itself to emit events would make the data layer know about the proxy server, which is a layering violation.

**Q3 (mid-upgrade ownership):** `KillInjected` propagates down the layer stack the same way `DataReceived` does. Each layer's `_handle_event` receives it; layers that don't own the flow's current protocol state ignore it. The topmost layer actively managing the flow (e.g., the HTTP layer if WebSocket upgrade is in progress) handles it by issuing `CloseConnection` commands on both client and server, then signals the `resume_event` if set. The `_handle_event` chain ensures exactly one layer acts on it.

**Q4 (scope vs #5484):** Conditional — If #5484 is the "kill doesn't wake `wait_for_resume`" variant (kill fires locally but the blocked coroutine never unblocks), `KillInjected` closes it because the event is delivered to the *running layer's* event handler, which clears the `_resume_event`. If #5484 is about a different race (e.g., kill on a CONNECT-pending-HTTP/2 flow that hasn't entered the HTTP/2 layer yet), it depends on whether the TCP layer handles the event for un-upgraded flows. The safe scope claim is #4711 only, with #5484 as "likely closed pending confirmation of the #5484 root cause."

**Implementation shape:**
```python
# events.py
@dataclass
class KillInjected(Event):
    flow: flow.Flow

# proxyserver.py
def inject_event(self, event: events.MessageInjected | events.KillInjected):
    ...

@command.command("inject.kill")  # mirrors inject.tcp
def inject_kill(self, flow: Flow):
    if not flow.killable:
        return
    flow.kill()  # pure state
    try:
        self.inject_event(events.KillInjected(flow))
    except ValueError:
        pass

# core.py flow.kill command updated to call inject_kill OR proxyserver.inject_kill directly
```

The single-class design (B) means all layers use `@expect(events.KillInjected)` — not a problem since every active layer should handle kill uniformly.
