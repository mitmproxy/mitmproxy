
# GLM-5.1 verdict: KillInjected event architecture for mitmproxy

Q1 (per-protocol vs generic): **B** — no payload to parameterize; subclasses add nothing.
Q2 (emission point): **C** — mirrors inject.tcp/udp/websocket exactly.
Q3 (mid-upgrade ownership): Event routes by connection ID via `inject_event`, then propagates down the active layer stack. `HttpStream.passthrough` forwards to child layer. `NextLayer` (undecided protocol) closes the connection directly. No per-type routing needed because the event is protocol-agnostic.
Q4 (scope vs #5484): **Yes** — both issues share the same root cause (kill is state mutation only, never enters the proxy event stream); injecting the event fixes both.

## OVERALL VERDICT

Add a single `KillInjected(Event)` dataclass in `mitmproxy/proxy/events.py` with a `flow: flow.Flow` field — no `Generic[T]`, no per-protocol subclasses. The `Generic[T]` on `MessageInjected` exists because message payloads have protocol-specific types; kill has no payload, so subclassing is pure boilerplate that a maintainer would flag as unnecessary pattern cargo-culting.

Emission follows the established `inject.*` command pattern: add `@command.command("inject.kill")` to `proxyserver.py` that calls `f.kill()` (state mutation) then creates a `KillInjected(flow)` and passes it to `self.inject_event(event)`. Rename `inject_event`'s type hint from `MessageInjected` to a union or base that includes `KillInjected`. Every existing call site (`core.py:flow.kill`, `view.py:remove`, `blocklist.py`, `serverplayback.py`, `disable_h2c.py`) switches to calling `inject.kill` instead of bare `f.kill()`.

Each layer adds `KillInjected` to its `@expect` decorators: TCP and UDP alongside `XxxMessageInjected`; `HttpLayer._handle_event` routes it to the correct stream (same path as line 971's `MessageInjected` handling); `HttpStream` handles it in every active state by issuing close commands. For mid-upgrade flows, the event naturally reaches whichever layer is active — `NextLayer` gets it and closes the connection; `HttpStream.passthrough` forwards to the child layer. No special routing logic required beyond what the existing event propagation already provides.

