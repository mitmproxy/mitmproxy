---
title: "Tools"
menu: "overview"
menu:
    overview:
        weight: 3
---

# Overview

You should think of the mitmproxy project's tools as a set of front-ends that
expose the same underlying functionality. We aim to have feature parity across
all of our tooling, and all tools share a common configuration mechanism and
most command-line options.

## mitmproxy

{{< figure src="/screenshots/mitmproxy.png" >}}

**mitmproxy** is a console tool that allows interactive examination and
modification of HTTP traffic. It differs from mitmdump in that all flows are
kept in memory, which means that it's intended for taking and manipulating
small-ish samples. Use the `?` shortcut key to view, context-sensitive
documentation from any **mitmproxy** screen.


## mitmweb

{{< figure src="/screenshots/mitmweb.png" >}}

**mitmweb** is mitmproxy's web-based user interface that allows
interactive examination and modification of HTTP traffic. Like
mitmproxy, it differs from mitmdump in that all flows are kept in
memory, which means that it's intended for taking and manipulating
small-ish samples.

{{% note %}}
Mitmweb is currently in beta. We consider it stable for all features
currently exposed in the UI, but it still misses a lot of mitmproxy's
features.
{{% /note %}}


## mitmdump

**mitmdump** is the command-line companion to mitmproxy. It provides
tcpdump-like functionality to let you view, record, and programmatically
transform HTTP traffic. See the `--help` flag output for complete
documentation.


### Example: Saving traffic

{{< highlight bash  >}}
mitmdump -w outfile
{{< / highlight >}}

Start up mitmdump in proxy mode, and write all traffic to **outfile**.

### Filtering saved traffic

{{< highlight bash  >}}
mitmdump -nr infile -w outfile "~m post"
{{< / highlight >}}

Start mitmdump without binding to the proxy port (`-n`), read all flows
from infile, apply the specified filter expression (only match POSTs),
and write to outfile.

### Client replay

{{< highlight bash  >}}
mitmdump -nc outfile
{{< / highlight >}}

Start mitmdump without binding to the proxy port (`-n`), then replay all
requests from outfile (`-c filename`). Flags combine in the obvious way,
so you can replay requests from one file, and write the resulting flows
to another:

{{< highlight bash  >}}
mitmdump -nc srcfile -w dstfile
{{< / highlight >}}

See the [client-side replay]({{< relref "overview-features#client-side-replay"
>}}) section for more information.

### Running a script

{{< highlight bash  >}}
mitmdump -s examples/add_header.py
{{< / highlight >}}

This runs the **add_header.py** example script, which simply adds a new
header to all responses.

### Scripted data transformation

{{< highlight bash  >}}
mitmdump -ns examples/add_header.py -r srcfile -w dstfile
{{< / highlight >}}

This command loads flows from **srcfile**, transforms it according to
the specified script, then writes it back to **dstfile**.

