---
title: "Addons"
menu:
    addons:
        weight: 1
---

# Addons

Mitmproxy's addon mechanism consists of a set of APIs that support components of
any complexity. Addons interact with mitmproxy by responding to **events**,
which allow them to hook into and change mitmproxy's behaviour. They are
configured through **[options]({{< relref concepts-options >}})**, which can be
set in mitmproxy's config file, changed interactively by users, or passed on the
command-line. Finally, they can expose **commands**, which allows users to
invoke their actions either directly or by binding them to keys in the
interactive tools.

Addons are an exceptionally powerful part of mitmproxy. In fact, much of
mitmproxy's own functionality is defined in [a suite of built-in
addons](https://github.com/mitmproxy/mitmproxy/tree/master/mitmproxy/addons),
implementing everything from functionality like [anticaching]({{< relref
"overview-features#anticache" >}}) and [sticky cookies]({{< relref
"overview-features#sticky-cookies" >}}) to our onboarding webapp. The built-in
addons make for instructive reading, and you will quickly see that quite complex
functionality can often boil down to a very small, completely self-contained
modules. Mitmproxy provides the exact same set of facilities it uses for its own
functionality to third-party scripters and extenders.

This document will show you how to build addons using **events**, **options**
and **commands**. However, this is not an API manual, and the mitmproxy source
code remains the canonical reference. One easy way to explore the API from the
command-line is to use [pydoc](https://docs.python.org/3/library/pydoc.html).
Here, for example, is a command that shows the API documentation for the
mitmproxy's HTTP flow classes:

{{< highlight bash  >}}
pydoc mimtproxy.http
{{< /highlight >}}

You will be referring to the mitmproxy API documentation frequently, so keep
**pydoc** or an equivalent handy.

# Anatomy of an addon

{{< example src="examples/addons/anatomy.py" lang="py" >}}

Above is a simple addon that keeps track of the number of flows (or more
specifically HTTP requests) we've seen. Every time it sees a new flow, it uses
mitmproxy's internal logging mechanism to announce its tally. The output can be
found in the event log in the interactive tools, or on the console in mitmdump.

Take it for a spin and make sure that it does what it's supposed to, by loading
it into your mitmproxy tool of choice. We'll use mitmpdump in these examples,
but the flag is identical for all tools:

{{< highlight bash  >}}
> mitmdump -s ./anatomy.py
{{< /highlight >}}

Here are a few things to note about the code above:

- Mitmproxy picks up the contents of the `addons` global list and loads what it
  finds into the addons mechanism.
- Addons are just objects - in this case our addon is an instance of `Counter`.
- The `request` method is an example of an **event**. Addons simply implement a
  method for each event they wan to handle. Each event has a signature
  consisting of arguments that are passed to the method. For `request`, this is
  an instance of `mitmproxy.http.HTTPFlow`.
- Finally, the `ctx` module is a holdall module that exposes a set of standard
  objects that are commonly used in addons. We could pass a `ctx` object as the
  first parameter to every event, but we've found it neater to just expose it as
  an importable global. In this case, we're using the `ctx.log` object to do our
  logging.