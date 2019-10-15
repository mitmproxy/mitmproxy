---
title: "Ignoring Domains"
menu:
    howto:
        weight: 2
---

# Ignoring Domains

There are two main reasons why you may want to exempt some traffic from
mitmproxy's interception mechanism:

- **Certificate pinning:** Some traffic is protected using [Certificate
  Pinning](https://security.stackexchange.com/questions/29988/what-is-certificate-pinning)
  and mitmproxy's interception leads to errors. For example, the Twitter app,
  Windows Update or the Apple App Store fail to work if mitmproxy is active.
- **Convenience:** You really don't care about some parts of the traffic and
  just want them to go away. Note that mitmproxy's "Limit" option is often the
  better alternative here, as it is not affected by the limitations listed
  below.

If you want to peek into (SSL-protected) non-HTTP connections, check out the
**tcp_proxy** feature. If you want to ignore traffic from mitmproxy's processing
because of large response bodies, take a look at the [streaming]({{< relref "overview-features#streaming" >}}) feature.


## ignore_hosts

The `ignore_hosts` option allows you to specify a regex which is matched against
a `host:port` string (e.g. "example.com:443") of a connection. Matching hosts
are excluded from interception, and passed on unmodified.

|                    |                                                                    |
| ------------------ | ------------------------------------------------------------------ |
| command-line alias | `--ignore-hosts regex`                                             |
| mitmproxy option   | `ignore_hosts` |


## Limitations

There are two important quirks to consider:

- **In transparent mode, the ignore pattern is matched against the IP and
  ClientHello SNI host.** While we usually infer the hostname from the Host
  header if the `ignore_hosts` option is set, we do not have access to this
  information before the SSL handshake. If the client uses SNI however, then we
  treat the SNI host as an ignore target.
- **In regular and upstream proxy mode, explicit HTTP requests are never
  ignored.**\[1\] The ignore pattern is applied on CONNECT requests, which
  initiate HTTPS or clear-text WebSocket connections.

## Tutorial

If you just want to ignore one specific domain, there's usually a bulletproof
method to do so:

1. Run mitmproxy or mitmdump in verbose mode (`-v`) and observe the `host:port`
    information in the serverconnect messages. mitmproxy will filter on these.
2. Take the `host:port` string, surround it with ^ and $, escape all dots (.
    becomes \\.) and use this as your ignore pattern:


{{< highlight none  >}}
>>> mitmdump -v
127.0.0.1:50588: clientconnect
127.0.0.1:50588: request
  -> CONNECT example.com:443 HTTP/1.1
127.0.0.1:50588: Set new server address: example.com:443
127.0.0.1:50588: serverconnect
  -> example.com:443
^C
>>> mitmproxy --ignore-hosts ^example\.com:443$
{{< /highlight >}}

Here are some other examples for ignore patterns:

{{< highlight none  >}}
# Exempt traffic from the iOS App Store (the regex is lax, but usually just works):
--ignore-hosts apple.com:443
# "Correct" version without false-positives:
--ignore-hosts '^(.+\.)?apple\.com:443$'

# Ignore example.com, but not its subdomains:
--ignore-hosts '^example.com:'

# Transparent mode:
--ignore-hosts 17\.178\.96\.59:443
# IP address range:
--ignore-hosts 17\.178\.\d+\.\d+:443
{{< / highlight >}}

This option can also be used to whitelist some domains through negative lookahead expressions. However, ignore patterns are always matched against the IP address of the target before being matched against its domain name. Thus, the pattern must allow any IP addresses using an expression like `^(?![0-9\.]+:)` in order for domains whitelisting to work. Here are examples of such patterns:

{{< highlight none  >}}
# Ignore everything but example.com and mitmproxy.org (not subdomains):
--ignore-hosts '^(?![0-9\.]+:)(?!example\.com:)(?!mitmproxy\.org:)'

# Ignore everything but example.com and its subdomains:
--ignore-hosts '^(?![0-9\.]+:)(?!([^\.:]+\.)*example\.com:)'
{{< / highlight >}}

**Footnotes**

1. This stems from an limitation of explicit HTTP proxying: A single connection
    can be re-used for multiple target domains - a `GET http://example.com/`
    request may be followed by a `GET http://evil.com/` request on the same
    connection. If we start to ignore the connection after the first request, we
    would miss the relevant second one.
