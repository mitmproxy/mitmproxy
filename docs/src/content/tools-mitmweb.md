---
title: "mitmweb"
menu: "tools"
menu:
    tools:
        weight: 3
---

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
