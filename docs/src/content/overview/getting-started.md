---
title: "Getting Started"
weight: 3
aliases:
  - /overview-getting-started/
---

# Getting Started

We assume you have already [installed]({{< relref "/overview/installation">}}) mitmproxy on
your machine.

## Launch the tool you need

You can start any of our three tools from the command line / terminal.

* **mitmproxy** gives you an interactive command-line interface
* **mitmweb** gives you a browser-based GUI
* **mitmdump** gives you non-interactive terminal output

## Configure your browser or device

Mitmproxy starts as a [regular HTTP proxy]({{< relref
"/concepts/modes#regular-proxy">}}) by default and listens on `http://localhost:8080`.

You need to configure your browser or device to route all traffic through mitmproxy.
Browser versions and configurations options frequently change, so we recommend to simply search the
web on how to configure an HTTP proxy for your system. Some operating system
have a global settings, some browser have their own, other applications use
environment variables, etc.

You can check that your web traffic is going through mitmproxy by browsing to
http://mitm.it - it should present you with a [simple page]({{< relref
"/concepts/certificates#quick-setup">}}) to install the mitmproxy Certificate
Authority - which is also the next step. Follow the instructions for your OS /
system and install the CA.

## Verifying everything works

At this point your running mitmproxy instance should already show the first HTTP
flows from your client. You can test that all TLS-encrypted web traffic is
working as expected by browsing to https://mitmproxy.org - it should show up as
new flow and you can inspect it.

## Resources

* [**GitHub**](https://github.com/mitmproxy/mitmproxy): If you want to ask usage questions, contribute
  to mitmproxy, or submit a bug report, please use GitHub.
