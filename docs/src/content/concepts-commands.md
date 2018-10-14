---
title: "Commands"
menu:
    concepts:
        weight: 6
---

# Commands

Commands are the mechanism that allows users to actively interact with addons.
Perhaps the most prominent example of this is the mitmproxy console user
interface - every interaction in this tool consists of commands bound to keys.
Commands also form a flexible and very powerful way to interact with mitmproxy
from the command prompt. In mitmproxy console you can enter the command prompt
with the `:` key. The prompt has intelligent tab completion for command names
and many of the built-in argument types - give it a try.

The canonical reference for commands is the `--commands` flag, which is exposed
by each of the mitmproxy tools. Passing this flag will dump an annotated list of
all registered commands, their arguments and their return values to screen. In
mimtproxy console you can also view a palette of all commands in the command
browser (by default accessible with the `C` key binding).


# Working with flows

Many of mitmproxy's commands take flows as arguments. For instance, the
signature for the client replay commands looks like this:

{{< highlight none  >}}
replay.client [flow]
{{< /highlight >}}


That means that it expects a sequence of one or more flows. This is where [flow
specifications]({{< relref concepts-filters >}}) come in - mitmproxy will
intelligently expand a flexible flow selection language to a list of flows when
invoking commands.

Fire up mitmproxy console, and intercept some traffic so we have flows to work
with. Now type the following command:

{{< highlight none  >}}
:replay.client @focus
{{< /highlight >}}

Make sure you try using tab completion for the command name and the flow
specification. The `@focus` specifiers expands to the currently focused flow, so
you should see this flow replay. However, replay can take any number of flows.
Try the following command:

{{< highlight none  >}}
:replay.client @all
{{< /highlight >}}

Now you should see all flows replay one by one. We have the full power of the
mitmproxy filter language at our disposal here, so we could also, for example,
just replay flows for a specific domain:

{{< highlight none  >}}
:replay.client "~d google.com"
{{< /highlight >}}










