---
title: "Scripting"
menu:
    addons:
        weight: 5
---

# Scripting

Sometimes, we would like to write a quick script without going through the
trouble of creating a class. The addons mechanism has a shorthand that allows a
module as a whole to be treated as an addon object. This lets us place event
handler functions in the module scope. For instance, here is a complete script
that adds a header to every request.


{{< example src="examples/addons/scripting-headers.py" lang="py" >}}


Here's another example that intercepts requests to a particular URL and sends
an arbitrary response instead:

{{< example src="examples/simple/send_reply_from_proxy.py" lang="py" >}}


You can look at the [http][] module, or the [Request][], and
[Response][] classes for other attributes that you can use when
scripting.

[http][]: https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/http.py
[Request]: https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/net/http/request.py
[Response]: https://github.com/mitmproxy/mitmproxy/blob/master/mitmproxy/net/http/response.py
