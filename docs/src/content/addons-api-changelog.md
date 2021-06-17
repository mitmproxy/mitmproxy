---
title: "API Changelog"
layout: single
menu:
    addons:
        weight: 9
---

# API Changelog

We try to avoid them, but this page lists breaking changes in the mitmproxy addon API.

## mitmproxy 7.0

#### Connection Events

We've revised mitmproxy's connection-specific event hooks as part of the new proxy core. See the new 
[event hook documentation]({{< relref "addons-api#ConnectionEvents" >}}) for details. As the passed objects are slightly
different now, we've also taken this opportunity to introduce a consistent event names:

| mitmproxy 6 | mitmproxy 7 |
|--|--|
| `clientconnect` | `client_connected` |
| `clientdisconnect` | `client_disconnected` |
| ❌ | `server_connect` |
| `serverconnect` | `server_connected` |
| `serverdisconnect` | `server_disconnected` |

#### Logging

The `log` event has been renamed to `add_log`. This fixes a consistent source of errors where users imported 
modules with the name "log", which were then inadvertedly picked up.

#### Contentviews

Contentviews now implement `render_priority` instead of `should_render`. This enables additional specialization, for
example one can now write contentviews that pretty-print only specific JSON responses.
See the [contentview.py]({{< relref "addons-examples#contentview" >}}) example for details.

#### WebSocket Flows

mitmproxy 6 had a custom WebSocketFlow class, which had 
[ugly co-dependencies with the related HTTPFlow](https://github.com/mitmproxy/mitmproxy/issues/4425). Long story short,
WebSocketFlow is no more and instead HTTPFlow has a neat 
[`.websocket` attribute]({{< relref "api/mitmproxy.http.md#HTTPFlow.websocket" >}}). All WebSocket flows are now passed
the originating `HTTPFlow` with this attribute set.
