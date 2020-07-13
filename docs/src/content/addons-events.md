---
title: "Events"
menu:
    addons:
        weight: 2
---

# Events

Addons hook into mitmproxy's internal mechanisms through events. These are
implemented on addons as methods with a set of well-known names. Many events
receive `Flow` objects as arguments - by modifying these objects, addons can
change traffic on the fly. For instance, here is an addon that adds a response
header with a count of the number of responses seen:

{{< example src="examples/addons/http-add-header.py" lang="py" >}}


## Supported Events

Below is an addon class that implements stubs for all events. We've added
annotations to illustrate the argument types for the various events.

### Generic Events

{{< example src="examples/addons/events.py" lang="py" >}}

### HTTP Events

{{< example src="examples/addons/events-http-specific.py" lang="py" >}}

### WebSocket Events

{{< example src="examples/addons/events-websocket-specific.py" lang="py" >}}

### TCP Events

{{< example src="examples/addons/events-tcp-specific.py" lang="py" >}}
