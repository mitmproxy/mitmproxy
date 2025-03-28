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

All contentviews implement the [`Contentview`] base class:

{{< example src="examples/addons/contentview.py" lang="py" >}}

### Render Priority

The following example demonstrates how to control the order of contentviews using [`render_priority`] and [`Metadata`]. Views with higher priority values appear first in the list of available views:

{{< example src="examples/addons/contentview-priority.py" lang="py" >}}


### Interactive Contentviews

The following example implements an interactive contentview that allows users to perform edits on the prettified representation:

{{< example src="examples/addons/contentview-interactive.py" lang="py" >}}

[`render_priority`]: {{< relref "api/mitmproxy.contentviews.md#Contentview.render_priority" >}}
[`Metadata`]: {{< relref "api/mitmproxy.contentviews.md#Metadata" >}}
[`Contentview`]: {{< relref "api/mitmproxy.contentviews.md#Contentview" >}}
