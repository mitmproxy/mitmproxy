---
title: "mitmdump"
menu: "tools"
menu:
    tools:
        weight: 2
---

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

