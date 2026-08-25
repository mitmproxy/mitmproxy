---
title: "Replay Requests"
weight: 4
url: /mitmproxytutorial-replayrequests/
has_asciinema: true
---

# Replay Requests

Another powerful feature of mitmproxy is replaying previous flows.
Two types of replays are supported:

* **Client-side Replay:** mitmproxy replays previous client requests, i.e., sends the same request to the server again.
* **Server-side Replay:** mitmproxy replays server responses for requests that match an earlier recorded request.

In this tutorial we focus on the more common use case of client-side replays.
See the docs for more info on [server-side replay]({{< relref "/overview/features#server-side-replay" >}}).

{{% asciicast file="mitmproxy_replay_requests" poster="0:3" instructions=true %}}

You are almost done with this tutorial. In the last step you find more mitmproxy-related resources to discover.
