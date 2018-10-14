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

{{< example src="examples/addons/addheader.py" lang="py" >}}


## Supported Events

Below is an addon class that implements stubs for all events. We've added
annotations to illustrate the argument types for the various events.

{{< example src="examples/addons/events.py" lang="py" >}}