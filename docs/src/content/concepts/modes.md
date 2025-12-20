---
title: "Proxy Modes"
weight: 2
aliases:
  - /concepts-modes/
---

# Proxy Modes

mitmproxy supports different proxy modes to capture traffic.
You can use any of the modes with any of the mitmproxy tools (mitmproxy, mitmweb, or mitmdump).


### Recommended

- [Regular](#regular-proxy): The default mode. Configure your client(s) to use an HTTP(S) proxy.
- [Local Capture](#local-capture): Capture applications on the same device.
- [WireGuard](#wireguard): Capture external devices or individual Android apps.
- [Reverse](#reverse-proxy): Put mitmproxy in front of a server.

### Advanced Modes

- [Transparent](#transparent-proxy): Capture traffic with custom network routes.
- [TUN Interface](#tun-interface): Create a virtual network device to capture traffic.
- [Upstream](#upstream-proxy): Chain two HTTP(S) proxies.
- [SOCKS](#socks-proxy): Run a SOCKS5 proxy server.
- [DNS](#dns-server): Run a scriptable DNS server.


## Regular Proxy

Mitmproxy's regular mode is the simplest and the most robust to set up.
If your target can be configured to use an HTTP proxy, we recommend you start with this.

1. Start `mitmproxy`, `mitmdump`, or `mitmweb`. You do not need to pass any arguments.
2. Configure your client to use mitmproxy by explicitly setting an HTTP
    proxy. By default, mitmproxy listens on port 8080.
3. Quick Check: You should already be able to visit an unencrypted HTTP
    site through the proxy.
4. Open the magic domain **mitm.it** and install the certificate for your
    device.

### Troubleshooting

1. If you do not see any traffic in mitmproxy, open mitmproxy's event log.
   You should be seeing `client connect` messages in there.
   If you do not see `client connect` messages, your client does not reach the proxy at all:
      - You have maybe misconfigured the IP address or port.
      - Alternatively your wireless network may use _client isolation_,
        which prevents clients from communicating with one another.
2. There are applications that bypass the operating system's HTTP proxy settings -
   Android applications are a common example. In these cases, you need to
   use mitmproxy's [WireGuard](#wireguard), [Local Capture](#local-capture), or [transparent](#transparent-proxy) modes.

#### Network Topology

If you are proxying an external device, your network will probably look
like this:

{{< figure src="/schematics/proxy-modes-regular.png" >}}

The square brackets signify the source and destination IP addresses.
Your client explicitly connects to mitmproxy and mitmproxy explicitly
connects to the target server.


## Local Capture

Local capture mode transparently captures traffic from applications running on the same device.
You can capture everything on the current device, or only a particular process name or process ID (PID):

```shell
mitmproxy --mode local       # Intercept everything on this machine.
mitmproxy --mode local:curl  # Intercept cURL only.
mitmproxy --mode local:42    # Intercept PID 42 only.
```

Local capture is implemented using low-level operating system APIs, so interception is transparent and the targeted
application is not aware of being proxied.

If you are curious about implementation details, check out the
[announcement blog posts](https://mitmproxy.org/tags/local-capture/). Local capture is available on Windows, Linux, and macOS.

#### Intercept Specs

The target selection can be negated by prepending an exclamation mark:

```shell
mitmproxy --mode local:!curl  # Intercept everything on this machine but cURL.
```

It is also possible to provide a comma-separated list:

```shell
mitmproxy --mode local:curl,wget    # Intercept cURL and wget only.
mitmproxy --mode local:!curl,!wget  # Intercept everything but cURL and wget.
```

#### Local Capture Limitations on Linux

- **Egress only:** mitmproxy will capture outbound connections only.
  For inbound connections, we recommend reverse proxy mode.
- **Root privileges:** To load the BPF program, mitmproxy needs to spawn a privileged subprocess using `sudo`.
  For the web UI, this means that mitmweb needs to be started directly with `--mode local` on the command line
  to get a sudo password prompt.
- **Kernel compatibility:** Our eBPF instrumentation requires a reasonably recent kernel.
  We officially support Linux 6.8 and above, which matches Ubuntu 22.04.
- **Intercept specs:** Program names are matched on the first 16 characters only (based on the kernel's [TASK_COMM_LEN]).
- **Containers:** Capturing traffic from containers will fail unless they use the host network.
  For example, containers can be started with `docker/podman run --network host`.
- **Windows Subsystem for Linux (WSL 1/2):** WSL is unsupported as eBPF is disabled by default.

[TASK_COMM_LEN]: https://github.com/torvalds/linux/blob/fbfd64d25c7af3b8695201ebc85efe90be28c5a3/include/linux/sched.h#L306

#### Local Capture Limitations on macOS

- **Egress only:** mitmproxy will capture outbound connections only.
  For inbound connections, we recommend reverse proxy mode.

## WireGuard

In WireGuard mode, mitmproxy starts a WireGuard VPN server. Devices can be connected using standard WireGuard client
applications and mitmproxy will transparently intercept their traffic.

1. Start `mitmweb --mode wireguard`.
2. Install a WireGuard client on target device.
3. Import the WireGuard client configuration provided by mitmproxy.

No additional routing configuration is required. The WireGuard server runs entirely in userspace,
so no administrative privileges are necessary in this mode.

### Configuration

#### WireGuard server

By default, the WireGuard server will listen on port `51820/udp`, the default
port for WireGuard servers. This can be changed by setting the `listen_port`
option or by specifying an explicit port (`--mode wireguard@51821`).

The encryption keys for WireGuard connections are stored in
`~/.mitmproxy/wireguard.conf`. It is possible to specify a custom path with
`--mode wireguard:path`. New keys will be generated automatically if the
specified file does not yet exist. For example, to connect two clients
simultaneously, you can run
`mitmdump --mode wireguard:wg-keys-1.conf --mode wireguard:wg-keys-2.conf@51821`.

#### WireGuard clients

It is possible to limit the IP addresses for which traffic is sent over the
WireGuard tunnel to specific ranges. In this case, the `AllowedIPs` setting
in the WireGuard client configuration can be changed from `0.0.0.0/0` (i.e
"route *all* IPv4 traffic through the WireGuard tunnel") to the desired ranges
of IP addresses (this setting allows multiple, comma-separated values).

For more complex network layouts it might also be necessary to override the
automatically detected `Endpoint` IP address (i.e. the address of the host on
which mitmproxy and its WireGuard server are running).

### Limitations

#### Transparently proxying mitmproxy host traffic

With the current implementation, it is not possible to proxy all traffic of the
host that mitmproxy itself is running on, since this would result in outgoing
WireGuard packets being sent over the WireGuard tunnel themselves.

#### Limited support for IPv6 traffic

The WireGuard server internal to mitmproxy supports receiving IPv6 packets from
client devices, but support for proxying IPv6 packets themselves is still
limited. For this reason, the `AllowedIPs` setting in generated WireGuard client
configurations does not list any IPv6 addresses yet. To enable the incomplete
support for IPv6 traffic, `::/0` (i.e. "route *all* IPv6 traffic through the
WireGuard tunnel") or other IPv6 address ranges can be added to the list of
allowed IP addresses.


## Reverse Proxy

```shell
mitmdump --mode reverse:https://example.com
```

In reverse proxy mode, mitmproxy acts as a normal server.
Requests by clients will be forwarded to a preconfigured target server,
and responses will be forwarded back to the client:

{{< figure src="/schematics/proxy-modes-reverse.png" >}}

### Listen Port

With the exception of DNS, reverse proxy servers will listen on port 8080 by default (DNS uses 53).
To listen on a different port, append `@portnumber` to the mode. You can
also pass `--mode` repeatedly to run multiple reverse proxy servers on different ports. For example,
the following command will run a reverse proxy server to example.com on port 80 and 443:

```text
mitmdump --mode reverse:https://example.com@80 --mode reverse:https://example.com@443
```

### Protocol Specification

The examples above have focused on HTTP reverse proxying, but mitmproxy can also reverse proxy other protocols.
To adjust the protocol, adjust the scheme in the proxy specification. For example, `--mode reverse:tcp://example.com:80`
would establish a raw TCP proxy.

| Scheme   | client ↔ mitmproxy                      | mitmproxy ↔ server |
|----------|-----------------------------------------|--------------------|
| http://  | HTTP or HTTPS (autodetected)            | HTTP               |
| https:// | HTTP or HTTPS (autodetected)            | HTTPS              |
| dns://   | DNS                                     | DNS                |
| http3:// | HTTP/3                                  | HTTP/3             |
| quic://  | Raw QUIC                                | Raw QUIC           |
| tcp://   | Raw TCP or TCP-over-TLS (autodetected)  | Raw TCP            |
| tls://   | Raw TCP or TCP-over-TLS (autodetected)  | Raw TCP-over-TLS   |
| udp://   | Raw UDP or UDP-over-DTLS (autodetected) | Raw UDP            |
| dtls://  | Raw UDP or UDP-over-DTLS (autodetected) | Raw UDP-over-DTLS  |


### Reverse Proxy Examples

- Say you have an internal API running at <http://example.local/>. You could now
  set up mitmproxy in reverse proxy mode at <http://debug.example.local/> and
  dynamically point clients to this new API endpoint, which provides them with
  the same data and you with debug information. Similarly, you could move your
  real server to a different IP/port and set up mitmproxy in the original
  place to debug and or redirect all sessions.
- Say you're a web developer working on <http://example.com/> (with a
  development version running on <http://localhost:8000/>). You can modify
  your hosts file so that example.com points to 127.0.0.1 and then run
  mitmproxy in reverse proxy mode on port 80. You can test your app on the
  example.com domain and get all requests recorded in mitmproxy.
- Say you have some toy project that should get TLS support. Simply set up
  mitmproxy as a reverse proxy on port 443 and you're done (`mitmdump -p 443
    --mode reverse:http://localhost:80/`). Mitmproxy auto-detects TLS traffic and intercepts
  it dynamically. There are better tools for this specific task, but mitmproxy
  is very quick and simple way to set up an TLS-speaking server.
- Want to know what goes on over (D)TLS (without HTTP)? With mitmproxy's raw
  traffic support you can. Use `--mode reverse:tls://example.com:1234` to
  spawn a TCP instance that connects to `example.com:1234` using TLS, and
  `--mode reverse:dtls://example.com:1234` to use UDP and DTLS respectively instead.
  Incoming client connections can either use (D)TLS themselves or raw TCP/UDP.
  In case you want to inspect raw traffic only for some hosts and HTTP for
  others, have a look at the [tcp_hosts]({{< relref "/concepts/options" >}}#tcp_hosts)
  and [udp_hosts]({{< relref "/concepts/options" >}}#udp_hosts) options.
- Say you want to capture DNS traffic to Google's Public DNS server? Then you
  can spawn a reverse instance with `--mode reverse:dns://8.8.8.8`. In case
  you want to resolve queries locally (ie. using the resolve capabilities
  provided and configured by your operating system), use [DNS Server](#dns-server)
  mode instead.

### Host Header

In reverse proxy mode, mitmproxy automatically rewrites the Host header to match
the upstream server. This allows mitmproxy to easily connect to existing
endpoints on the open web (e.g. `mitmproxy --mode reverse:https://example.com`). You can
disable this behaviour with the `keep_host_header` option.

However, keep in mind that absolute URLs within the returned document or HTTP
redirects will NOT be rewritten by mitmproxy. This means that if you click on a
link for "<http://example.com>" in the returned web page, you will be taken
directly to that URL, bypassing mitmproxy.

One possible way to address this is to modify the hosts file of your OS so that
"example.com" resolves to your proxy's IP, and then access the proxy by going
directly to example.com. Make sure that your proxy can still resolve the
original IP, or specify an IP in mitmproxy.

{{% note %}}

### Caveat: Interactive Use

Reverse Proxy mode is usually not sufficient to create a copy of an
interactive website at different URL. The HTML served to the client
remains unchanged - as soon as the user clicks on an non-relative URL
(or downloads a non-relative image resource), traffic no longer passes
through mitmproxy.
{{% /note %}}


## Transparent Proxy

{{% note %}}
Consider using [WireGuard](#wireguard) and [local capture](#local-capture) mode instead of transparent mode.
They are easier to set up and also support UDP-based protocols (which transparent mode currently does not).
{{% /note %}}

*Availability: Linux, macOS*

In transparent mode, traffic is directed into a proxy at the network
layer, without any client configuration required. This makes transparent
proxying ideal for situations where you can't change client behaviour:

```shell
mitmdump --mode transparent
```

In the graphic below, a machine running mitmproxy has been inserted
between the router and the internet:

{{< figure src="/schematics/proxy-modes-transparent-1.png" >}}

The square brackets signify the source and destination IP addresses.
Round brackets mark the next hop on the *Ethernet/data link* layer. This
distinction is important: when the packet arrives at the mitmproxy
machine, it must still be addressed to the target server. This means
that Network Address Translation should not be applied before the
traffic reaches mitmproxy, since this would remove the target
information, leaving mitmproxy unable to determine the real destination.

{{< figure src="/schematics/proxy-modes-transparent-wrong.png" >}}

### Common Configurations

There are many ways to configure your network for transparent proxying.
We'll look at two common scenarios:

1. Configuring the client to use a custom gateway/router/"next hop"
2. Implementing custom routing on the router

In most cases, the first option is recommended due to its ease of use.

#### (a) Custom Gateway

One simple way to get traffic to the mitmproxy machine with the
destination IP intact, is to simply configure the client with the
mitmproxy box as the default gateway.

{{< figure src="/schematics/proxy-modes-transparent-2.png" >}}

In this scenario, we would:

1. Configure the proxy machine for transparent mode. You can find instructions
    in the [transparent]({{< relref "/howto/transparent"
    >}}) section.
2. Configure the client to use the proxy machine's IP as the default gateway.
3. Quick Check: At this point, you should already be able to visit an
    unencrypted HTTP site over the proxy.
4. Open the magic domain **mitm.it** and install the certificate for your
    device.

Setting the custom gateway on clients can be automated by serving the
settings out to clients over DHCP. This lets set up an interception
network where all clients are proxied automatically, which can save time
and effort.

{{% note %}}

### Troubleshooting Transparent Mode

Incorrect transparent mode configurations are a frequent source of
error. If it doesn't work for you, try the following things:

- Open mitmproxy's event log - do you see clientconnect messages? If not, the
    packets are not arriving at the proxy. One common cause is the occurrence of
    ICMP redirects, which means that your machine is telling the client that
    there's a faster way to the internet by contacting your router directly (see
    the [transparent]({{< relref "/howto/transparent"
    >}}) section on how to disable them). If in doubt,
    [Wireshark](https://wireshark.org/) may help you to see whether something
    arrives at your machine or not.
- Make sure you have not explicitly configured an HTTP proxy on the client. This
    is not needed in transparent mode.
- Re-check the instructions in the [transparent]({{< relref "/howto/transparent"
    >}}) section. Anything you missed?

If you encounter any other pitfalls that should be listed here, please
let us know!
{{% /note %}}

#### (b) Custom Routing

In some cases, you may need more fine-grained control of which traffic
reaches the mitmproxy instance, and which doesn't. You may, for
instance, choose only to divert traffic to some hosts into the
transparent proxy. There are a huge number of ways to accomplish this,
and much will depend on the router or packet filter you're using. In
most cases, the configuration will look like this:

{{< figure src="/schematics/proxy-modes-transparent-3.png" >}}

## TUN Interface

*Availability: Linux*

```shell
sudo mitmdump --mode tun
```

In TUN mode, mitmproxy creates a virtual network interface on the system.
All traffic routed to this interface  will be intercepted by mitmproxy.
For example, `curl --interface tun0 http://example.com/` will be transparently
intercepted. For most applications, you will need to manually configure your local routing table.

You can optionally specify a fixed interface name:

```shell
sudo mitmdump --mode tun:mitm-tun
```

This mode requires root privileges (or `CAP_NET_ADMIN` on the Python interpreter) to create the tun interface.

#### Usage with Containers

Mitmproxy's [docker-entrypoint.sh] drops all privileges on startup by default.
To make TUN mode work in a container on Linux, you can do something like this:

```shell
docker run --privileged --network host mitmproxy/mitmproxy bash -c "mitmdump --mode tun"
```

[docker-entrypoint.sh]: https://github.com/mitmproxy/mitmproxy/blob/main/release/docker/docker-entrypoint.sh

## Upstream Proxy

```shell
mitmdump --mode upstream:http://example.com:8081
```

If you want to chain proxies by adding mitmproxy in front of a different
proxy appliance, you can use mitmproxy's upstream mode. In upstream
mode, all requests are unconditionally transferred to an upstream proxy
of your choice.

{{< figure src="/schematics/proxy-modes-upstream.png" >}}

mitmproxy supports both explicit HTTP and explicit HTTPS in upstream
proxy mode. You could in theory chain multiple mitmproxy instances in a
row, but that doesn't make any sense in practice (i.e. outside of our
tests).

## SOCKS Proxy

```shell
mitmdump --mode socks5
```

In this mode, mitmproxy acts as a SOCKS5 proxy.
This is similar to the regular proxy mode, but using SOCKS5 instead of HTTP for connection establishment
with the proxy.


## DNS Server

```shell
mitmdump --mode dns
```

This mode will listen for incoming DNS queries and use the resolve
capabilities of your operating system to return an answer. For A/AAAA
queries you can opt to ignore the system's hosts file using the
[`dns_use_hosts_file`]({{< relref "/concepts/options" >}}#dns_use_hosts_file)
option. Custom name servers for lookups can be specified using the
[`dns_name_servers`]({{< relref "/concepts/options" >}}#dns_name_servers)
option. By default port 53 will be used. To specify a different port, say 5353,
use `--mode dns@5353`.
