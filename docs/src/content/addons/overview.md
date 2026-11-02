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

# Entry Points (Plugins)

In addition to loading scripts via `-s`, mitmproxy supports auto-loading addons registered via Python entry points in the `mitmproxy.addons` group. This allows Python packages distributed via PyPI or wheels to integrate seamlessly with mitmproxy without requiring manual `-s` script paths:

```bash
pip install mitmproxy-addon-foo
mitmdump
```

Or using `uvx`:

```bash
uvx --from mitmproxy --with mitmproxy-addon-foo mitmdump
```

### Registering an Entry Point Addon

In your package's `pyproject.toml`, register the addon under the `mitmproxy.addons` entry point group:

```toml
[project.entry-points."mitmproxy.addons"]
my_addon = "my_package.addon:MyAddon"
```

The entry point may point to:
- An addon class (instantiated with zero arguments)
- A zero-argument factory function returning an addon instance or a sequence of addon instances
- An addon module or instance

### Contracts & Guarantees

- **Trust Model**: Third-party packages installed in your Python environment run with ambient user privileges. Only install trusted packages.
- **Ordering**: Built-in core and tool addons are registered first. Entry point addons load after built-ins, sorted deterministically in alphabetical order by entry point name (`ep.name`).
- **Name Reservation**: Entry point addons cannot override or collide with reserved built-in or tool addon names (such as `core`, `dumper`, `webaddon`, etc.). Conflicting entry points are logged with an error and skipped.
- **Opt-Out**: Automatic loading of entry point addons can be disabled by setting either the `MITMPROXY_NO_ENTRYPOINTS=1` or `MITMPROXY_NO_PLUGINS=1` environment variable.

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

Because addons are regular Python files, the easiest way to unit-test
them is to import the module from your test, instantiate the addon, and
call the event handler directly. For more complex testing needs, 
see [`test/mitmproxy/addons`](https://github.com/mitmproxy/mitmproxy/tree/main/test/mitmproxy/addons)
(but please note that internal testing helpers have no guaranteed stable API).
