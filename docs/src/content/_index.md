---
title: "Introduction"
layout: single
menu:
    overview:
        weight: 1
---

# Introduction

mitmproxy is a set of tools that provide an interactive, SSL/TLS-capable intercepting proxy for HTTP/1, HTTP/2, and WebSockets.

## Features

- Intercept HTTP & HTTPS requests and responses and modify them on the fly
- Save complete HTTP conversations for later replay and analysis
- Replay the client-side of an HTTP conversations
- Replay HTTP responses of a previously recorded server
- Reverse proxy mode to forward traffic to a specified server
- Transparent proxy mode on macOS and Linux
- Make scripted changes to HTTP traffic using Python
- SSL/TLS certificates for interception are generated on the fly
- And [much, much more...]({{< relref "overview-features">}})

## 3 Powerful Core Tools

The mitmproxy project's tools are a set of front-ends that expose common
underlying functionality. When we talk about "mitmproxy" we usually refer to any of the three tools - they
are just different front-ends to the same core proxy.

**mitmproxy** is an interactive, SSL/TLS-capable intercepting proxy with a console interface for HTTP/1, HTTP/2, and WebSockets.

**mitmweb** is a web-based interface for mitmproxy.

**mitmdump** is the command-line version of mitmproxy. Think tcpdump for HTTP.

Distribution packages can be found on the [mitmproxy website](https://mitmproxy.org).
Development information and our source code can be found in our
[GitHub repository](https://github.com/mitmproxy/mitmproxy).

### mitmproxy

{{< figure src="/screenshots/mitmproxy.png" >}}

**mitmproxy** is a console tool that allows interactive examination and
modification of HTTP traffic. It differs from mitmdump in that all flows are
kept in memory, which means that it's intended for taking and manipulating
small-ish samples. Use the `?` shortcut key to view, context-sensitive
documentation from any **mitmproxy** screen.

---

### mitmweb

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

---

### mitmdump

**mitmdump** is the command-line companion to mitmproxy. It provides
tcpdump-like functionality to let you view, record, and programmatically
transform HTTP traffic. See the `--help` flag output for complete
documentation.

#### Example: Saving traffic

```bash
mitmdump -w outfile
```

Start up mitmdump in proxy mode, and write all traffic to **outfile**.

#### Filtering saved traffic

```bash
mitmdump -nr infile -w outfile "~m post"
```

Start mitmdump without binding to the proxy port (`-n`), read all flows
from infile, apply the specified filter expression (only match POSTs),
and write to outfile.

#### Client replay

```bash
mitmdump -nC outfile
```

Start mitmdump without binding to the proxy port (`-n`), then replay all
requests from outfile (`-C filename`). Flags combine in the obvious way,
so you can replay requests from one file, and write the resulting flows
to another:

```bash
mitmdump -nC srcfile -w dstfile
```

See the [client-side replay]({{< relref "overview-features#client-side-replay"
>}}) section for more information.

#### Running a script

```bash
mitmdump -s examples/simple/add_header.py
```

This runs the **add_header.py** example script, which simply adds a new
header to all responses.

#### Scripted data transformation

```bash
mitmdump -ns examples/simple/add_header.py -r srcfile -w dstfile
```

This command loads flows from **srcfile**, transforms it according to
the specified script, then writes it back to **dstfile**.
