---
title: "API Changelog"
weight: 9
aliases:
  - /addons-api-changelog/
---

# API Changelog

We try to avoid them, but this page lists breaking changes in the mitmproxy addon API.

## mitmproxy 12

The Contentviews API has drastically simplified, see the new [contentview documentation] for details.

[contentview documentation]: {{< relref "/addons/contentviews" >}}

`mitmproxy.dns.Message` has been renamed to `mitmproxy.dns.DNSMessage`.

## mitmproxy 9.1

`mitmproxy.connection.Client` and `mitmproxy.connection.Server` now accept keyword arguments only.

## mitmproxy 9.0

#### Logging

We've deprecated mitmproxy's homegrown logging system in favor of Python's builtin `logging` module.
This means that addons should now use standard logging functionality instead of `mitmproxy.ctx.log`:

```python
# Deprecated:
from mitmproxy import ctx
ctx.log.info("hello world")

# New:
import logging
logging.info("hello world")
```


Accordingly, the `add_log` event has been deprecated. Developers who rely on log entries should register their own 
`logging.Handler` instead. An example for this can be found in the `EventStore` addon.

## mitmproxy 7.0

#### Connection Events

We've revised mitmproxy's connection-specific event hooks as part of the new proxy core. The `.client_conn` and 
`.server_conn` objects have major API changes across the board. See the new 
[event hook documentation]({{< relref "/addons/event-hooks#ConnectionEvents" >}}) for details. 

| Attribute      | Client (v6) | Server (v6)       | mitmproxy v7 |
|----------------|-------------|-------------------|--------------|
| Remote IP:Port | `.address`  | `.ip_address`     | `.peername`  |
| Local IP:Port  | ❌          | `.source_address` | `.sockname`  |
| Remote Domain  | N/A         | `.address`        | `.address`   |


As the passed objects are different now, we've also taken this opportunity to introduce more consistent event names:

| mitmproxy 6        | mitmproxy 7           |
| ------------------ | --------------------- |
| `clientconnect`    | `client_connected`    |
| `clientdisconnect` | `client_disconnected` |
| ❌                 | `server_connect`      |
| `serverconnect`    | `server_connected`    |
| `serverdisconnect` | `server_disconnected` |

#### Logging

The `log` event has been renamed to `add_log`. This fixes a consistent source of errors where users imported 
modules with the name "log", which were then inadvertedly picked up.

#### Contentviews

Contentviews now implement `render_priority` instead of `should_render`. This enables additional specialization, for
example one can now write contentviews that pretty-print only specific JSON responses.
See the [contentview.py]({{< relref "/addons/examples#contentview" >}}) example for details.

#### WebSocket Flows

mitmproxy 6 had a custom WebSocketFlow class, which had 
[ugly co-dependencies with the related HTTPFlow](https://github.com/mitmproxy/mitmproxy/issues/4425). Long story short,
WebSocketFlow is no more and instead HTTPFlow has a neat 
[`.websocket` attribute]({{< relref "api/mitmproxy.http.md#HTTPFlow.websocket" >}}). All WebSocket flows are now passed
the originating `HTTPFlow` with this attribute set. As always, existing dumpfiles are automatically converted on load.

#### Certificates

mitmproxy now uses `cryptography` instead of `pyOpenSSL` to generate certificates. As a consequence, the API of
`mitmproxy.certs` has changed.

#### HTTP Headers

`mitmproxy.net.http.Headers` -> `mitmproxy.http.Headers` for consistency.
