---
title: "Scripting"
menu:
    addons:
        weight: 5
---

# Scripting HTTP/1.1 and HTTP/2.0

Sometimes, we would like to write a quick script without going through the
trouble of creating a class. The addons mechanism has a shorthand that allows a
module as a whole to be treated as an addon object. This lets us place event
handler functions in the module scope. For instance, here is a complete script
that adds a header to every request.

{{< example src="examples/addons/scripting-minimal-example.py" lang="py" >}}


Here's another example that intercepts requests to a particular URL and sends
an arbitrary response instead:

{{< example src="examples/addons/http-reply-from-proxy.py" lang="py" >}}

All events around the HTTP protocol [can be found here]({{< relref "addons-events#http-events">}}).

For HTTP-related objects, please look at the [http][] module, or the
[Request][], and [Response][] classes for other attributes that you can use when
scripting.

# Scripting WebSocket

The WebSocket protocol initially looks like a regular HTTP request, before the client and server agree to upgrade the connection to WebSocket. All scripting events for initial HTTP handshake, and also the dedicated WebSocket events [can be found here]({{< relref "addons-events#websocket-events">}}).

{{< example src="examples/addons/websocket-simple.py" lang="py" >}}

For WebSocket-related objects please look at the [websocket][] module to find
all attributes that you can use when scripting.

[websocket]: https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/websocket.py


# Scripting TCP

All events around the TCP protocol [can be found here]({{< relref "addons-events#tcp-events">}}).

{{< example src="examples/addons/tcp-simple.py" lang="py" >}}

For WebSocket-related objects please look at the [tcp][] module to find
all attributes that you can use when scripting.

[tcp]: https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/tcp.py
