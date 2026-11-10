
### Voice 1

Q1 (per-protocol vs generic): B — no payload, one lifecycle concept  
Q2 (emission point):          C — command-shaped API, pure Flow model  
Q3 (mid-upgrade ownership):   Route by connection handler, not flow type. Let the active layer stack consume/propagate the kill.  
Q4 (scope vs #5484):          Conditional — PR1 likely covers intercepted wakeup; PR2 only if command path emits kill.

OVERALL VERDICT: Implement one `KillInjected(flow)` event. Expose it through an `inject.kill` proxyserver API that preserves `Flow.kill()` as pure state mutation. This is the most reviewable shape because it follows the event architecture without inventing protocol subclasses that carry no protocol data.

### Voice 2

Q1 (per-protocol vs generic): B — fake subclasses invite reviewer pushback  
Q2 (emission point):          C — mirrors injection without coupling data model  
Q3 (mid-upgrade ownership):   The connection/layer stack owns kill semantics. `inject_event` should not guess from `HTTPFlow`/`TCPFlow`/WebSocket state.  
Q4 (scope vs #5484):          Conditional — yes only if `x` on intercepted flows uses same injected path.

OVERALL VERDICT: Keep the public kill command authoritative: mutate flow state, then inject a generic kill event into the live connection handler. Mid-upgrade cases are exactly why routing must be runtime-stack-based rather than per-protocol-class-based. Per-protocol kill events would make WebSocket upgrade edge cases awkward for no payload-type benefit.

### Voice 3

Q1 (per-protocol vs generic): B — lifecycle event, not typed message data  
Q2 (emission point):          C — explicit proxy event boundary  
Q3 (mid-upgrade ownership):   The current active layer owns the abort. If it cannot handle it, normal event propagation should continue downward.  
Q4 (scope vs #5484):          No/Conditional — #5484 is intercepted-request behavior; claim only if tested.

OVERALL VERDICT: Add `KillInjected` beside `MessageInjected`, but do not mirror the subclass matrix. The event should be injected by addon/proxyserver command plumbing, not by `Flow.kill()`. Tests should cover in-transit HTTP and at least one upgrade-ish path where flow type dispatch would be wrong.

### Converged Verdict

Implement **Q1=B** and **Q2=C**: a single `events.KillInjected(flow)` plus an `inject.kill` proxyserver command/API, with `Flow.kill()` remaining a pure state mutation. The user-facing `flow.kill` command should use that API so all UI/addon paths both mark the flow killed and notify the live proxy handler. For mid-upgrade ownership, inject by `flow.client_conn.id` into the existing connection handler and let the active layer stack handle or propagate the event; do not route based on nominal flow type. Scope the PR to #4711 unless tests prove the same command path also fixes #5484.

Sources checked: [#4711](https://github.com/mitmproxy/mitmproxy/issues/4711), [#5484](https://github.com/mitmproxy/mitmproxy/issues/5484).

