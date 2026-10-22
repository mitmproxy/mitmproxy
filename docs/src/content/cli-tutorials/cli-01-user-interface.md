---
title: "User Interface"
weight: 1
url: /mitmproxytutorial-userinterface/
has_asciinema: true
---

# User Interface

First of all, we need to become familiar with mitmproxy's user interface.
Open the terminal window in which you started mitmproxy.
You are in the default view of mitmproxy, which shows a list of flows.
You should see your browser's HTTP requests to load this tutorial.
mitmproxy adds rows to the view as new requests come in.

{{% asciicast file="mitmproxy_user_interface" poster="0:3" instructions=true %}}

## Save a response body

To save the response body of the focused flow, press `b` in the flow list or flow view and enter a destination path, for example `response.json`. This uses `cut.save @focus response.content <path>` and writes only the response body, without HTTP headers. For a JSON API response, the saved file contains the JSON payload.

In the next lesson, you will learn to intercept requests before sending them to the server.
