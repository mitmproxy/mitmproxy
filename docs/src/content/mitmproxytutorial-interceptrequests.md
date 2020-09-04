---
title: "Intercept Requests"
menu:
    mitmproxytutorial:
        weight: 2
has_asciinema: true
---

# Intercept Requests

A powerful feature of mitmproxy is the interception of requests.
An intercepted request is paused so that the user can modify (or discard) the request before sending it to the server.
mitmproxy's `set intercept` command configures interceptions.
The command is bound to shortcut `i` by default.

Intercepting *all* requests is usually not desired as it constantly interrupts your browsing.
Thus, mitmproxy expects a [flow filter expression]({{< relref "concepts-filters" >}}) as the first argument to `set intercept` to selectively intercept requests.
In the tutorial below we use the flow filter `~u <regex>` that filters flows by matching the regular expressing on the URL of the request.

{{% asciicast file="mitmproxy_intercept_requests" poster="0:3" instructions=true %}}

In the next lesson, you will learn to modify intercepted flows before sending them to the server.
