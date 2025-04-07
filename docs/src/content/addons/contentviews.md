---
title: "Custom Contentviews"
weight: 6
menu:
    addons:
        weight: 6
---

# Custom Contentviews

Contentviews pretty-print binary message data that would otherwise be unreadable for humans. For some contentviews, the pretty-printed representation can be edited and mitmproxy is able to re-encode it into a binary message.

### Simple Example

All contentviews implement the [Contentview] base class:

{{< example src="examples/addons/contentview.py" lang="py" >}}

The view with the highest priority will be auto-selected. Builtin views return a priority between 0 and 1.


See [`mitmproxy.contentviews`] for the full API documentation.


### Interactive Contentviews

The following example implements an interactive contentview that allows users to perform edits on the prettified representation:

{{< example src="examples/addons/contentview-interactive.py" lang="py" >}}

[`mitmproxy.contentviews`]: {{< relref "api/mitmproxy.contentviews.md" >}}
[Contentview]: {{< relref "api/mitmproxy.contentviews.md#Contentview" >}}
