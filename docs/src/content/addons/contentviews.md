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

## Simple Example

All contentviews implement the [Contentview] base class:

{{< example src="examples/addons/contentview.py" lang="py" >}}

To use this contentview, load it as a regular addon:

```shell
mitmproxy -s examples/addons/contentview.py
```

Like all other mitmproxy addons, contentviews are hot-reloaded when their file contents change. 
mitmproxy (but not mitmweb) will automatically re-render the contentview as well.

For more details, see the [`mitmproxy.contentviews` API documentation].


## Syntax Highlighting

Contentviews always return an unstyled `str`, but they can declare that their output matches one of the 
predefined [`SyntaxHighlight` formats]. In particular, binary formats may prettify to YAML (or JSON) and
use the YAML highlighter.

The list of supported formats is currently limited, but the implementation is based on [tree-sitter] 
and easy to extend (see the [`mitmproxy-highlight` crate]).

## Interactive Contentviews

The following example implements an interactive contentview that allows users to perform edits on the prettified 
representation:

{{< example src="examples/addons/contentview-interactive.py" lang="py" >}}

[`mitmproxy.contentviews` API documentation]: {{< relref "api/mitmproxy.contentviews.md" >}}
[Contentview]: {{< relref "api/mitmproxy.contentviews.md#Contentview" >}}
[`SyntaxHighlight` formats]: {{< relref "api/mitmproxy.contentviews.md#Contentview.syntax_highlight" >}}
[`mitmproxy-highlight` crate]: https://github.com/mitmproxy/mitmproxy_rs/tree/main/mitmproxy-highlight/src
[tree-sitter]: https://tree-sitter.github.io/tree-sitter/