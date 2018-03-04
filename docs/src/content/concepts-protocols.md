---
title: "Protocols"
menu:
    concepts:
        weight: 7
---

# Protocols

## HTTP/1.0 and HTTP/1.1

[RFC7230: HTTP/1.1: Message Syntax and Routing](http://tools.ietf.org/html/rfc7230)

[RFC7231: HTTP/1.1: Semantics and Content](http://tools.ietf.org/html/rfc7231)

HTTP/1.0 and HTTP/1.1 support in mitmproxy is based on our custom HTTP stack,
which takes care of all semantics and on-the-wire parsing/serialization tasks.

mitmproxy currently does not support HTTP trailers - but if you want to send
us a PR, we promise to take look!

## HTTP/2

[RFC7540: Hypertext Transfer Protocol Version 2 (HTTP/2)](http://tools.ietf.org/html/rfc7540>)

HTTP/2 support in mitmproxy is based on
[hyper-h2](https://github.com/python-hyper/hyper-h2). It fully encapsulates the
internal state of HTTP/2 connections and provides an easy-to-use event-based
API. mitmproxy supports the majority of HTTP/2 feature and tries to
transparently pass-through as much information as possible.

mitmproxy currently does not support HTTP/2 trailers - but if you want to send
us a PR, we promise to take look!

mitmproxy currently does not support HTTP/2 Cleartext (h2c) since none of the
major browser vendors have implemented it.

Some websites are still having problems with correct HTTP/2 support in their
webservers and can cause errors, dropped connectiones, or simply no response at
all. We are trying to be as tolerant and forgiving as possible with the types of
data we send and receive, but
[some](https://github.com/mitmproxy/mitmproxy/issues/1745)
[faulty](https://github.com/mitmproxy/mitmproxy/issues/2823)
[implementations](https://github.com/mitmproxy/mitmproxy/issues/1824)
[simply](https://github.com/mitmproxy/mitmproxy/issues/1891) don't work well
with mitmproxy.

In order to increase the compatibility of mitmproxy with HTTP/2 webservers, we
default to NOT forward any priority information that is sent by a client. You
can enable it with: `http2_priority=true`.

## WebSocket

[RFC6455: The WebSocket Protocol](http://tools.ietf.org/html/rfc6455)

[RFC7692: Compression Extensions for WebSocket](http://tools.ietf.org/html/rfc7692)

WebSocket support in mitmproxy is based on [wsproto]
(https://github.com/python-hyper/wsproto) project. It fully encapsulates
WebSocket frames/messages/connections and provides an easy-to-use event-based
API.

mitmproxy fully supports the compression extension for WebSocket messages,
provided by wsproto. Message contents are automatically compressed and
decompressed before firing events.

mitmproxy currently does not display WebSocket messages in the console or web
UI. Only the WebSocket handshake flow is shown, which contains a reference to
the parent flow for all messages exchanged over this connection.

If an endpoint sends a PING to mitmproxy, a PONG will be sent back immediately
(with the same payload if present). To keep the other connection alive, a new
PING (without a payload) is sent to the other endpoint. Unsolicited PONG's are
not forwarded. All PING's and PONG's are logged (with payload if present).

## Raw TCP / TCP Proxy / Fallback

In case mitmproxy does not handle a specific protocol, you can exempt
hostnames from processing, so that mitmproxy acts as a generic TCP forwarder.
This feature is closely related to the *passthrough* functionality,
but differs in two important aspects:

  * The raw TCP messages are printed to the event log.
  * SSL connections will be intercepted.

Please note that message interception or modification are not possible yet. If
you are not interested in the raw TCP messages, you should use the ignore
domains feature.

|                    |                    |
| ------------------ | ------------------ |
| command-line alias | `--tcp HOST`       |
| mitmproxy shortcut | press `O` then `T` |
