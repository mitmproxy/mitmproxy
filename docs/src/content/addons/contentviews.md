---
title: "Custom Contentviews"
weight: 6
menu:
    addons:
        weight: 6
---

# Custom Contentviews

Contentviews pretty-print binary message data (e.g. HTTP response bodies) that would otherwise be hard to understand for
humans. Some contentviews are also _interactive_, i.e. the pretty-printed representation can be edited and mitmproxy 
will re-encode it into a binary message.

### Simple Example

All contentviews implement the [Contentview] base class:

{{< example src="examples/addons/contentview.py" lang="py" >}}

The contentview can be loaded as a regular addon:

```shell
mitmproxy -s examples/addons/contentview.py
```


See [`mitmproxy.contentviews`] for the API documentation.


### Interactive Contentviews

The following example implements an interactive contentview that allows users to perform edits on the prettified representation:

{{< example src="examples/addons/contentview-interactive.py" lang="py" >}}

[`mitmproxy.contentviews`]: {{< relref "api/mitmproxy.contentviews.md" >}}
[Contentview]: {{< relref "api/mitmproxy.contentviews.md#Contentview" >}}
