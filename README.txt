
**pathod** is a pathological HTTP/S daemon, useful for testing and torturing
HTTP clients. At **pathod**'s heart is a tiny, terse language for crafting HTTP
responses. The simplest way to use **pathod** is to fire up the daemon, and
specify the response behaviour you want using this language in the request URL.
Here's a minimal example:

    http://localhost:9999/p/200

Everything after the "/p/" path component is a response specifier - in this
case just a vanilla 200 OK response. See the complete docs to get (much)
fancier. You can also add anchors to the **pathod** server that serve a fixed
response whenever a matching URL is requested:

    pathod --anchor "/foo=200"

Here, "/foo" a regex specifying the anchor path, and the part after the "=" is
a response specifier.

**pathod** also has a nifty built-in web interface, which lets you play with
the language by previewing responses, exposes activity logs, online help and
various other goodies. Try it by visiting the server root:

    http://localhost:9999

