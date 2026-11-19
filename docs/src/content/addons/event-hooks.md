---
title: "Event Hooks"
weight: 2
# this is important so that the relative links in the generated file work.
url: api/events.html
aliases:
    - /addons-events/
---

# Event Hooks

Addons hook into mitmproxy's internal mechanisms through event hooks. These are
implemented on addons as methods with a set of well-known names. Many events
receive `Flow` objects as arguments - by modifying these objects, addons can
change traffic on the fly. For instance, here is an addon that adds a response
header with a count of the number of responses seen:

{{< example src="examples/addons/http-add-header.py" lang="py" >}}

## Lifecycle Order

During startup, addons see the lifecycle events in this order:

1. `load` – called when the addon is first loaded. Use it to add options and commands.
2. `configure` – called when options change. During startup, it is called once with all options in the updated set.
3. `running` – called when the proxy is completely up and running. At this point, all addons are loaded and all options are set.
4. `done` – called when the addon shuts down. This is guaranteed to be the final event an addon sees.

`configure` may be called again at any time while mitmproxy is running whenever an option changes, and `done` is also called when an addon is removed. All other events (connections, HTTP, DNS, …) only fire between `running` and `done`.

## Available Hooks

The following addons list all available event hooks.

{{< readfile file="/generated/api/events.html" >}}
