---
title: "Filter expressions"
menu:
    concepts:
        weight: 4
---

# Filter expressions

Many commands in the mitmproxy tool make use of filter expressions. Filter
expressions consist of the following operators:


<table class="table filtertable"><tbody>
<tr><th>~a</th><td>Match asset in response: CSS, Javascript, Flash, images.</td></tr>
<tr><th>~b regex</th><td>Body</td></tr>
<tr><th>~bq regex</th><td>Request body</td></tr>
<tr><th>~bs regex</th><td>Response body</td></tr>
<tr><th>~c int</th><td>HTTP response code</td></tr>
<tr><th>~d regex</th><td>Domain</td></tr>
<tr><th>~dst regex</th><td>Match destination address</td></tr>
<tr><th>~e</th><td>Match error</td></tr>
<tr><th>~h regex</th><td>Header</td></tr>
<tr><th>~hq regex</th><td>Request header</td></tr>
<tr><th>~hs regex</th><td>Response header</td></tr>
<tr><th>~http</th><td>Match HTTP flows</td></tr>
<tr><th>~m regex</th><td>Method</td></tr>
<tr><th>~marked</th><td>Match marked flows</td></tr>
<tr><th>~q</th><td>Match request with no response</td></tr>
<tr><th>~s</th><td>Match response</td></tr>
<tr><th>~src regex</th><td>Match source address</td></tr>
<tr><th>~t regex</th><td>Content-type header</td></tr>
<tr><th>~tcp</th><td>Match TCP flows</td></tr>
<tr><th>~tq regex</th><td>Request Content-Type header</td></tr>
<tr><th>~ts regex</th><td>Response Content-Type header</td></tr>
<tr><th>~u regex</th><td>URL</td></tr>
<tr><th>~websocket</th><td>Match WebSocket flows</td></tr>
<tr><th>!</th><td>unary not</td></tr>
<tr><th>&</th><td>and</td></tr>
<tr><th>|</th><td>or</td></tr>
<tr><th>(...)</th><td>grouping</td></tr>
</tbody></table>


- Regexes are Python-style
- Regexes can be specified as quoted strings
- Header matching (~h, ~hq, ~hs) is against a string of the form "name: value".
- Strings with no operators are matched against the request URL.
- The default binary operator is &.


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
