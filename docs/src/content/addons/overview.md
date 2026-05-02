---
title: "Overview"
weight: 1
aliases:
  - /addons-overview/
---

# Addons

Mitmproxy's addon mechanism is an exceptionally powerful part of mitmproxy. In fact, much of mitmproxy's own
functionality is defined in
[a suite of built-in addons](https://github.com/mitmproxy/mitmproxy/tree/main/mitmproxy/addons),
implementing everything from functionality like
[anticaching]({{< relref "/overview/features#anticache" >}}) and [sticky cookies]({{< relref
"/overview/features#sticky-cookies" >}}) to our onboarding webapp.

Addons interact with mitmproxy by responding to [events]({{< relref event-hooks >}}), which allow them to hook into and
change mitmproxy's behaviour. They are configured through [options]({{< relref "/addons/options" >}}), which can be set in
mitmproxy's config file, changed interactively by users, or passed on the command-line. Finally, they can expose
[commands]({{< relref "/addons/commands" >}}), which allows users to invoke their actions either directly or by binding
them to keys in the interactive tools.

# Anatomy of an addon

{{< example src="examples/addons/anatomy.py" lang="py" >}}

Above is a simple addon that keeps track of the number of flows (or more
specifically HTTP requests) we've seen. Every time it sees a new flow, it
increments and logs its tally. The output can be found in the event log in the
interactive tools, or on the console in mitmdump.

Take it for a spin and make sure that it does what it's supposed to, by loading
it into your mitmproxy tool of choice. We'll use mitmdump in these examples,
but the flag is identical for all tools:

```bash
mitmdump -s ./anatomy.py
```

Here are a few things to note about the code above:

- Mitmproxy picks up the contents of the `addons` global list and loads what it
  finds into the addons mechanism.
- Addons are just objects - in this case our addon is an instance of `Counter`.
- The `request` method is an example of an *event*. Addons simply implement a
  method for each event they want to handle. Each event and its signature are documented
  in the [API documentation]({{< relref "event-hooks" >}}).

# Abbreviated Scripting Syntax

Sometimes, we would like to write a quick script without going through the trouble of creating a class.
The addons mechanism has a shorthand that allows a module as a whole to be treated as an addon object.
This lets us place event handler functions in the module scope.
For instance, here is a complete script that adds a header to every request:

{{< example src="examples/addons/anatomy2.py" lang="py" >}}

# Developing Addons

## Live Reloading

Scripts loaded with `-s path/to/script.py` are watched for changes.
Whenever the file's modification time changes, mitmproxy unregisters the
old module, re-imports the file, and re-registers the new addon — without
restarting the proxy or losing the state of any other addons or in-flight
flows. This means you can edit your addon in your editor and the changes
take effect on the next save (within roughly one second).

Errors raised at import time, in `configure`, or in `running` are logged
to the event log and the previous version of the addon is left
unregistered. Fix the error and save the file again to retry. Errors
raised inside event handlers (`request`, `response`, …) are logged but do
not unload the addon.

## Testing Addons

Because addons are plain Python objects, the easiest way to unit-test
them is to import the module from your test, instantiate the addon, and
call the event handler directly with a flow built by
`mitmproxy.test.tflow`. The `mitmproxy.test.taddons.context()` context
manager wires up `ctx` (options, master, logger) so addons that read
`ctx.options` or call `ctx.master` work the same way they do when loaded
by mitmproxy.

For the `Counter` addon from `anatomy.py` above:

```python
from mitmproxy.test import taddons, tflow
from anatomy import Counter

def test_counter_increments_on_request():
    addon = Counter()
    with taddons.context(addon):
        addon.request(tflow.tflow())
        addon.request(tflow.tflow())
        assert addon.num == 2
```

For tests that need the full event sequence (load, configure, request,
response, …), `await tctx.cycle(addon, flow)` runs through it from an
`async def` test. Mitmproxy's own test suite under
`test/mitmproxy/addons/` is a good place to look for patterns when
testing more complex hooks.
