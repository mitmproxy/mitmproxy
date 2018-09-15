---
title: "Introduction"
layout: single
menu:
    overview:
        weight: 1
---

# Introduction

The mitmproxy project's tools are a set of front-ends that expose common
underlying functionality.

**mitmproxy** is an interactive, SSL/TLS-capable intercepting proxy with a console interface for HTTP/1, HTTP/2, and WebSockets.

**mitmdump** is the command-line version of mitmproxy. Think tcpdump for HTTP.

**mitmweb** is a web-based interface for mitmproxy.

Documentation, tutorials and distribution packages can be found on the
[mitmproxy website](https://mitmproxy.org).

Development information and our source code can be found in our
[GitHub repository](https://github.com/mitmproxy/mitmproxy).


## Features

- Intercept HTTP & HTTPS requests and responses and modify them on the fly
- Save complete HTTP conversations for later replay and analysis
- Replay the client-side of an HTTP conversations
- Replay HTTP responses of a previously recorded server
- Reverse proxy mode to forward traffic to a specified server
- Transparent proxy mode on macOS and Linux
- Make scripted changes to HTTP traffic using Python
- SSL/TLS certificates for interception are generated on the fly
- And much, much more...
