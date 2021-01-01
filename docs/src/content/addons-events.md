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

Below we list events supported by mitmproxy. We've added
annotations to illustrate the argument types.

{{< readfile file="/generated/events.html" markdown="true" >}}
