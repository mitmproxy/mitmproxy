
Q1 (per-protocol vs generic): B — No payload type to specialize; subclasses are boilerplate without reason.

`MessageInjected[T]` is generic because `T` varies (TCPMessage, WebSocketMessage, etc.). `KillInjected` carries only `flow: Flow` — there is no type parameter. Per-protocol subclasses would exist solely to mirror the `MessageInjected` shape, not to express a real type distinction. The HTTP multiplexer already checks `isinstance(event, events.MessageInjected)` at the base class level (events.py:122) and routes generically — a single `KillInjected` plugs directly into that dispatch path. Per-protocol subclasses would force either (a) every `isinstance` check to enumerate four subclasses, or (b) checking the base class anyway, making the subclasses dead code. A maintainer reviewing Option A will ask "what does TcpKillInjected do differently from UdpKillInjected?" and the honest answer is "nothing" — that's a rejection-risk.

Q2 (emission point): C — New `inject.kill` command mirrors the existing `inject.*` pattern exactly.

Option A (emit from `Flow.kill()`) breaks layering: `flow.py` is a data class today with zero proxy-event imports. Adding `events.KillInjected` and `proxyserver.inject_event` creates a circular dependency (flow → events → flow) and couples the data model to the proxy server — a structural regression.

Option B (emit from the `flow.kill` addon command) works but is inconsistent: every other injection path goes through `inject.<verb>` in `proxyserver.py`. The TUI, web UI, and console all call `flow.kill` the command, which already works. Adding `inject.kill` as the canonical emission point means:
- `inject.kill(flow)` calls `flow.kill()` + `inject_event(KillInjected(flow))`
- The existing `flow.kill` command is refactored to call `inject.kill`
- Web UI's `KillFlow`/`KillFlows` handlers call `inject.kill` instead of `f.kill()` directly

This mirrors exactly how `inject.tcp` works: the addon command constructs the event, calls `inject_event`, and handles the `ValueError` for dead connections. The only difference is `KillInjected` has no message payload — the command signature is simpler: `inject.kill(flow)` with no `to_client`/`message` parameters.

Q3 (mid-upgrade ownership): Let the event propagate down the layer stack; the active layer handles it.

With a single `KillInjected` class, there's no routing ambiguity — the event enters the connection handler via `inject_event` (same as `MessageInjected`) and flows through the layer stack via `event_to_child`. The HTTP multiplexer already has the pattern for this (http/__init__.py:971-990): look up the flow's connection in `self.connections`, find the active stream, and dispatch. If the flow is mid-upgrade (CONNECT pending, WebSocket handshake in progress), the pre-upgrade layer is still active and receives the event. That layer closes the underlying transport — which is the correct behavior (kill means "drop this connection now," not "wait for the upgrade to finish then kill"). TLS-over-TCP-over-CONNECT works because events propagate through the entire layer stack; `KillInjected` follows the same path as `DataReceived`.

Q4 (scope vs #5484): No — #5484 is already closed by PR #8199.

#5484 ("pressing X doesn't kill an intercepted request") was the same root cause as #8045: `kill()` didn't wake `_resume_event`, so the post-hook teardown (which already handles kill correctly) never ran. PR #8199 fixes this by setting `_resume_event` in `kill()`. The `KillInjected` event solves #4711 (killing flows *not* intercepted, genuinely in transit with the server) — a different problem. PR2 should claim #4711 only. If the reviewer asks about #5484, point to PR #8199 as the fix.

OVERALL VERDICT: Single `KillInjected(Event)` dataclass with `flow: Flow` field, no per-protocol subclasses. Emitted via a new `inject.kill` command in `proxyserver.py` that calls `flow.kill()` then `inject_event(KillInjected(flow))`. The event propagates through the layer stack like any other event; layers that need to handle it add `KillInjected` to their `@expect` decorator and close the connection on receipt. The existing `flow.kill` command, web UI handlers, and console keybinding all route through `inject.kill`. This is the minimal-diff path that respects the existing layering, mirrors the `inject.*` pattern the maintainer already established, and avoids the "why are these different?" review trap of per-protocol subclasses.

