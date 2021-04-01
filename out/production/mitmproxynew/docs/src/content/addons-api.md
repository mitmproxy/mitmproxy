---
title: "Event Hooks & API"
url: "api/events.html"
aliases:
    - /addons-events/
layout: single
menu:
    addons:
        weight: 3
---

# Event Hooks

Addons hook into mitmproxy's internal mechanisms through event hooks. These are
implemented on addons as methods with a set of well-known names. Many events
receive `Flow` objects as arguments - by modifying these objects, addons can
change traffic on the fly. For instance, here is an addon that adds a response
header with a count of the number of responses seen:

{{< example src="examples/addons/http-add-header.py" lang="py" >}}

## Available Hooks

The following addons list all available event hooks.

{{< readfile file="/generated/api/events.html" >}}
