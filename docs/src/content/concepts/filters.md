---
title: "Filter expressions"
weight: 4
aliases:
  - /concepts-filters/
---

# Filter expressions

Many commands in the mitmproxy tool make use of filter expressions. Filter
expressions consist of the following operators:

{{< readfile file="/generated/filters.html" >}}

- Regexes are Python-style.
- Regexes can be specified as quoted strings.
- Regexes are case-insensitive by default.[^1]
- Header matching (~h, ~hq, ~hs) is against a string of the form "name: value".
- Strings with no operators are matched against the request URL.
- The default binary operator is &.

[^1]: This can be disabled by setting `MITMPROXY_CASE_SENSITIVE_FILTERS=1`
  as an environment variable.

## View flow selectors

In interactive contexts, mitmproxy has a set of convenient flow selectors that
operate on the current view:

<table class="table filtertable"><tbody>
<tr><th>@all</th><td>All flows</td></tr>
<tr><th>@focus</th><td>The currently focused flow</td></tr>
<tr><th>@shown</th><td>All flows currently shown</td></tr>
<tr><th>@hidden</th><td>All flows currently hidden</td></tr>
<tr><th>@marked</th><td>All marked flows</td></tr>
<tr><th>@unmarked</th><td>All unmarked flows</td></tr>
</tbody></table>

These are frequently used in commands and key bindings.

## Examples

URL containing "google.com":

    google\.com

Requests whose body contains the string "test":

    ~q ~b test

Anything but requests with a text/html content type:

    !(~q & ~t "text/html")

Replace entire GET string in a request (quotes required to make it work):

    ":~q ~m GET:.*:/replacement.html"
