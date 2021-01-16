---
title: "Protocols"
menu:
    concepts:
        weight: 7
---

# Protocols

mitmproxy not only supports HTTP, but also other important web protocols.
This page lists details and known limitations of the respective protocol implementations.
Most protocols can be disabled by toggling the respective [option]({{< relref concepts-options >}}).

## HTTP/1.x

HTTP/1.0 and HTTP/1.1 support in mitmproxy is based on our custom HTTP stack, which is particularly robust to HTTP syntax
errors. Protocol violations are often deliberately forwarded or inserted at the proxy.

##### Known Limitations

- Trailers: mitmproxy currently does not support HTTP trailers, but we are happy to accept contributions.

##### RFCs

- [RFC7230: HTTP/1.1: Message Syntax and Routing](http://tools.ietf.org/html/rfc7230)
- [RFC7231: HTTP/1.1: Semantics and Content](http://tools.ietf.org/html/rfc7231)

## HTTP/2

HTTP/2 support in mitmproxy is based on [hyper-h2](https://github.com/python-hyper/hyper-h2). In case the upstream
server does not speak HTTP/2, mitmproxy seamlessly translates messages to HTTP/1.

##### Known Limitations

- *Trailers*: mitmproxy currently does not support HTTP trailers, but we are happy to accept contributions.
- *Priority Information*: mitmproxy currently ignores HTTP/2 PRIORITY frames. This does not affect the transmitted
  contents, but potentially affects the order in which messages are sent.
- *Push Promises*: mitmproxy currently does not advertise support for HTTP/2 Push Promises.
- *Cleartext HTTP/2*: mitmproxy currently does not support unencrypted HTTP/2 (h2c).

##### RFCs

- [RFC7540: Hypertext Transfer Protocol Version 2 (HTTP/2)](http://tools.ietf.org/html/rfc7540)

## WebSocket

WebSocket support in mitmproxy is based on [wsproto](https://github.com/python-hyper/wsproto) project, including support
for message compression.

##### Known Limitations

- *User Interface*: WebSocket messages are currently logged to the event log, but not displayed in the console or web
  interface. We would welcome contributions that fix this issue.
- *Replay*: Client or server replay is not possible yet.
- *Ping*: mitmproxy will forward PING and PONG frames, but not store them. The payload is only logged to the event log.
- *Unknown Extensions*: Unknown WebSocket extensions will cause a warning message to be logged, but are otherwise passed
  through as-is. This may lead to noncompliant behavior.

##### RFCs

- [RFC6455: The WebSocket Protocol](http://tools.ietf.org/html/rfc6455)
- [RFC7692: Compression Extensions for WebSocket](http://tools.ietf.org/html/rfc7692)

## Generic TCP Proxy

Mitmproxy can also act as a generic TCP proxy. In this mode, mitmproxy will still detect the presence of TLS at the
beginning of a connection and perform a man-in-the-middle attack if necessary, but otherwise forward messages
unmodified.

Users can explicitly opt into generic TCP proxying by setting the [`tcp_hosts` option]({{< relref concepts-options >}}).

##### Known Limitations

- *Replay*: Client or server replay is not possible yet.
- *Opportunistic TLS*: mitmproxy will not detect when a plaintext protocol upgrades to TLS (STARTTLS).
