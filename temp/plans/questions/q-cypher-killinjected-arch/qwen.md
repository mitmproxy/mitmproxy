
Q1 (per-protocol vs generic): [B] — Kill has no payload; per-protocol subclasses add boilerplate with zero semantic differentiation.

Q2 (emission point):          [B] — `Flow.kill()` stays a pure dataclass mutation; the addon emits the event, mirroring `inject.tcp`/`inject.websocket` exactly.

Q3 (mid-upgrade ownership):   `inject_event` routes by `flow.client_conn.id` to the connection's top layer. If `NextLayer` hasn't resolved the protocol, the kill event buffers in its event queue and replays to whichever layer wins the race — TCP or HTTP. The HTTP layer should handle `KillInjected` by closing the stream and both connections; TCP/WS/UDP layers close their connections. No propagation needed; the top layer that owns the sockets acts.

Q4 (scope vs #5484):          [No] — #5484 ("X doesn't kill intercepted flow") is Closed and was the exact bug PR1 (#8199) fixed. PR2 closes #4711 only ("kill flows in transit").

OVERALL VERDICT: Single `KillInjected(flow: Flow)` event class in `mitmproxy/proxy/events.py`. The `core.kill` command (and TUI/web kill handlers) call `f.kill()` for the state mutation, then construct `KillInjected(f)` and call `proxyserver.inject_event()`. The `inject_event` method routes by `client_conn.id` as it already does for `MessageInjected`. The HTTP layer gains an `isinstance(event, events.KillInjected)` branch alongside the existing `MessageInjected` handling at `http/__init__.py:971`, closing the stream and both client/server connections. TCP, WebSocket, and UDP layers add `KillInjected` to their `@expect` decorators and issue `CloseConnection` for both sides. The `NextLayer` buffer handles mid-upgrade gracefully — the event queues and replays to whichever protocol layer resolves. No per-protocol subclasses, no coupling of `flow.py` to proxy events, no new proxyserver commands.

