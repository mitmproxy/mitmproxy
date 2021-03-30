---
title: "Addons"
menu:
    addons:
        weight: 1
---

# Addons

Mitmproxy's addon mechanism is an exceptionally powerful part of mitmproxy. In fact, much of mitmproxy's own
functionality is defined in
[a suite of built-in addons](https://github.com/mitmproxy/mitmproxy/tree/main/mitmproxy/addons),
implementing everything from functionality like
[anticaching]({{< relref "overview-features#anticache" >}}) and [sticky cookies]({{< relref
"overview-features#sticky-cookies" >}}) to our onboarding webapp.

Addons interact with mitmproxy by responding to [events]({{< relref addons-api >}}), which allow them to hook into and
change mitmproxy's behaviour. They are configured through [options]({{< relref addons-options >}}), which can be set in
mitmproxy's config file, changed interactively by users, or passed on the command-line. Finally, they can expose
[commands]({{< relref addons-commands >}}), which allows users to invoke their actions either directly or by binding
them to keys in the interactive tools.

# Anatomy of an addon

{{< example src="examples/addons/anatomy.py" lang="py" >}}

Above is a simple addon that keeps track of the number of flows (or more
specifically HTTP requests) we've seen. Every time it sees a new flow, it uses
mitmproxy's internal logging mechanism to announce its tally. The output can be
found in the event log in the interactive tools, or on the console in mitmdump.

Take it for a spin and make sure that it does what it's supposed to, by loading
it into your mitmproxy tool of choice. We'll use mitmpdump in these examples,
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
  in the [API documentation]({{< relref "addons-api" >}}).
- Finally, the `ctx` module is a holdall module that exposes a set of standard
  objects that are commonly used in addons. We could pass a `ctx` object as the
  first parameter to every event, but we've found it neater to just expose it as
  an importable global. In this case, we're using the `ctx.log` object to do our
  logging.

# Abbreviated Scripting Syntax

Sometimes, we would like to write a quick script without going through the trouble of creating a class.
The addons mechanism has a shorthand that allows a module as a whole to be treated as an addon object.
This lets us place event handler functions in the module scope.
For instance, here is a complete script that adds a header to every request:

{{< example src="examples/addons/anatomy2.py" lang="py" >}}
