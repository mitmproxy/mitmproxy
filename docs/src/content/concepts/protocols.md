---
title: "Protocols"
weight: 7
aliases:
  - /concepts-protocols/
---

# Protocols

mitmproxy not only supports HTTP, but also other important web protocols.
This page lists details and known limitations of the respective protocol implementations.
Most protocols can be disabled by toggling the respective [option]({{< relref "/concepts/options" >}}).

## HTTP/1

HTTP/1.0 and HTTP/1.1 support in mitmproxy is based on our custom HTTP stack based on
[h11](https://github.com/python-hyper/h11), which is particularly robust to HTTP syntax
errors. Protocol violations are often deliberately forwarded or inserted at the proxy.

##### Known Limitations

- Trailers: mitmproxy currently does not support trailers with HTTP/1.x, but we are happy to accept contributions.

## HTTP/2

HTTP/2 support in mitmproxy is based on [hyper-h2](https://github.com/python-hyper/hyper-h2). In case the upstream
server does not speak HTTP/2, mitmproxy seamlessly translates messages to HTTP/1.

##### Known Limitations

- *Priority Information*: mitmproxy currently ignores HTTP/2 PRIORITY frames. This does not affect the transmitted
  contents, but potentially affects the order in which messages are sent.
- *Push Promises*: mitmproxy currently does not advertise support for HTTP/2 Push Promises.
- *Cleartext HTTP/2*: mitmproxy currently does not support unencrypted HTTP/2 (h2c).

## HTTP/3

HTTP/3 support in mitmproxy is based on [aioquic](https://github.com/aiortc/aioquic). Mitmproxy's HTTP/3 functionality
is available in reverse proxy, local and WireGuard mode.

##### Known Limitations

- *Replay*: Client Replay is currently broken.
- *Supported Versions*: mitmproxy currently only supports QUIC Version 1. Version 2 (RFC 9369) is not supported yet.
- *Implementation Compatibility*: mitmproxy's HTTP/3 support has only been extensively tested with cURL.
  Other implementations are likely to exhibit bugs.

## WebSocket

WebSocket support in mitmproxy is based on [wsproto](https://github.com/python-hyper/wsproto) project, including support
for message compression.

##### Known Limitations

- *Replay*: Client or server replay is not possible yet.
- *Ping*: mitmproxy will forward PING and PONG frames, but not store them. The payload is only logged to the event log.
- *Unknown Extensions*: Unknown WebSocket extensions will cause a warning message to be logged, but are otherwise passed
  through as-is. This may lead to noncompliant behavior.

## DNS

DNS support in mitmproxy is based on a custom DNS implementation.

##### Known Limitations

- *Replay*: Client or server replay is not possible yet.
- We have not started any work on DoT/DoH/DoQ (DNS-over-TLS/HTTPS/QUIC) yet. Contributions are welcome.

## Generic TCP/TLS Proxy

Mitmproxy can also act as a generic TCP proxy. In this mode, mitmproxy will still detect the presence of TLS at the
beginning of a connection and perform a man-in-the-middle attack if necessary, but otherwise forward messages
unmodified.

Users can explicitly opt into generic TCP proxying by setting the [`tcp_hosts` option]({{< relref "/concepts/options" >}}).

##### Known Limitations

- *Replay*: Client or server replay is not possible yet.
- *Opportunistic TLS*: mitmproxy will not detect when a plaintext protocol upgrades to TLS (STARTTLS).


## Generic UDP/DTLS Proxy

Mitmproxy can also act as a generic UDP proxy. In this mode, mitmproxy will still detect the presence of DTLS at the
beginning of a connection and perform a man-in-the-middle attack if necessary, but otherwise forward messages
unmodified.

Users can explicitly opt into generic UDP proxying by setting the [`udp_hosts` option]({{< relref "/concepts/options" >}}).

##### Known Limitations

- *Replay*: Client or server replay is not possible yet.
