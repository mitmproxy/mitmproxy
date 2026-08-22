
# deepseek verdict — KillInjected architecture for mitmproxy #4711

**Voice: deepseek-v4-pro** | Date: 2026-04-29

Key finding: `Flow.kill()` has three call sites — `core.py:92` (flow.kill command), `blocklist.py:77` (addon-initiated kill), and `tools/web/app.py` (web UI). Any emission point narrower than `Flow.kill()` itself leaves call sites silently broken for in-transit flows. This is the decisive factor for Q2.

```
Q1 (per-protocol vs generic): B — No payload to parameterize; reviewer would ask "why four copies?"
Q2 (emission point):          A — Three call sites; only Flow.kill() covers blocklist + web UI
Q3 (mid-upgrade ownership):   Event propagates existing handle_event chain; active layer owns it.
                              Single generic class avoids protocol-ambiguity at emission time.
Q4 (scope vs #5484):          No — #5484 is interception-path (resume_event), fixed by PR1;
                              KillInjected targets in-transit path (#4711), orthogonal mechanism.

OVERALL VERDICT: One generic `@dataclass class KillInjected(Event)` in events.py, carrying only `flow: flow.Flow`.
Emitted from `Flow.kill()` via a callback/injector reference set by the proxyserver at connection time — same
pattern as the existing `_resume_event` attribute, keeping flow.py free of proxyserver imports. TCP/UDP/WebSocket
layers add `KillInjected` to their existing `@expect` decorators alongside `DataReceived` and `ConnectionClosed`,
and handle it by transitioning to `done` and issuing `CloseConnection` commands for both ends. HTTP layers already
check `flow.live` between yields (correct post-PR1); KillInjected closes the orthogonal gap where a layer generator
is blocked on a `CommandCompleted` yield rather than `wait_for_resume`. PR description scoped to #4711 only;
#5484 is already resolved by PR1's `_resume_event` fix.
```

## Reasoning per question

### Q1 — B (single generic)

`MessageInjected[T]` has per-protocol subclasses because `message: T` varies by protocol (TCPMessage vs UDPMessage vs WebSocketMessage). The generics serve a real type-safety purpose. `KillInjected` carries zero protocol-specific data — no payload, no type parameter. Per-protocol subclasses (`TcpKillInjected`, `UdpKillInjected`, `WebSocketKillInjected`, `HttpKillInjected`) would each be an identical one-liner `class XxxKillInjected(KillInjected): ...` with zero behavioral difference. A reviewer — especially Maximilian Hils, who writes terse, intentional code — would flag this. The `@expect` decorator sharing concern is moot: `DataReceived` and `ConnectionClosed` are already shared across all layers, proving this is idiomatic.

### Q2 — A (Flow.kill() itself)

Three concrete call sites for `Flow.kill()`: `core.py:92` (UI-initiated), `blocklist.py:77` (addon-initiated), and `tools/web/app.py` (web UI). If the event is emitted only from the `flow.kill` command (Option B) or a new `inject.kill` command (Option C), then blocklist-based kills and web UI kills silently fail to terminate in-transit flows — a correctness regression. Emitting from `Flow.kill()` covers all paths with a single change point — exactly what the maintainer's TODO (which lives in `Flow.kill()`) implies. Coupling concern: `Flow` already holds `_resume_event` (an asyncio primitive set by the layer). The same pattern works — store an optional `_kill_injector: Callable | None` on the flow, set by the connection handler at registration time. Flow.py imports `KillInjected` from events.py but never touches proxyserver.py.

### Q3 — Event propagation through existing routing

With a single generic `KillInjected` (Q1=B), routing is trivial: `inject_event` resolves `connection_id` from `flow.client_conn.id` → `handler.server_event(event)` → `layer.handle_event(event)`. The currently active `_handle_event` target receives it, regardless of protocol state. If a flow is mid-upgrade (HTTP CONNECT not yet upgraded), the `HttpLayer` is still active; it forwards through `HttpStream` or handles directly. TLS-over-TCP-over-CONNECT: outer layer forwards to `NextLayer._handle_event` → delegates to inner layer — same propagation path as `DataReceived`. No special routing, no ambiguity. This is a secondary argument for Q1=B: per-protocol subclasses force you to decide which subclass to instantiate at emission time, when the flow's protocol state may be ambiguous.

### Q4 — Scope: #5484 is separate

#5484 describes killing an *intercepted* (paused) HTTP flow via the `x` key. In this scenario, the layer generator is blocked on `wait_for_resume()`, not on a `CommandCompleted` yield. `Flow.kill()` calls `_resume_event.set()`, which wakes `wait_for_resume`, which returns to the layer, which checks `flow.live == False` and stops. This is the `_resume_event` path. PR1 (#8199) fixed the wakeup mechanism — #5484 is resolved by PR1 alone. `KillInjected` targets the *in-transit* case (#4711), where the generator is mid-I/O (blocked on `SendData`/`OpenConnection` command completion) and `flow.live = False` is never checked because the generator hasn't resumed. The two mechanisms are complementary, not overlapping.

