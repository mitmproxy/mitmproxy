---
title: "Transparent Proxying"
menu:
    howto:
        weight: 1
---

# Transparent Proxying

When a transparent proxy is used, traffic is redirected into a proxy at the
network layer, without any client configuration being required. This makes
transparent proxying ideal for those situations where you can't change client
behaviour - proxy-oblivious mobile applications being a common example.

To set up transparent proxying, we need two new components. The first is a
redirection mechanism that transparently reroutes a TCP connection destined for
a server on the Internet to a listening proxy server. This usually takes the
form of a firewall on the same host as the proxy server -
[iptables](http://www.netfilter.org/) on Linux or
[pf](https://en.wikipedia.org/wiki/PF_(firewall)) on OSX. When the proxy
receives a redirected connection, it sees a vanilla HTTP request, without a host
specification. This is where the second new component comes in - a host module
that allows us to query the redirector for the original destination of the TCP
connection.

At the moment, mitmproxy supports transparent proxying on OSX Lion and above,
and all current flavors of Linux.

## Linux

On Linux, mitmproxy integrates with the iptables redirection mechanism to
achieve transparent mode.

### 1. Enable IP forwarding.

```bash
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1
```

This makes sure that your machine forwards packets instead of rejecting them.

If you want to persist this across reboots, you need to adjust your `/etc/sysctl.conf` or
a newly created `/etc/sysctl.d/mitmproxy.conf` (see [here](https://superuser.com/a/625852)).

### 2. Disable ICMP redirects.

```bash
sysctl -w net.ipv4.conf.all.send_redirects=0
```

If your test device is on the same physical network, your machine shouldn't inform the device that
there's a shorter route available by skipping the proxy.

If you want to persist this across reboots, see above.

### 3. Create an iptables ruleset that redirects the desired traffic to mitmproxy.

Details will differ according to your setup, but the ruleset should look
something like this:

```bash
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080
iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080
ip6tables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080
ip6tables -t nat -A PREROUTING -i eth0 -p tcp --dport 443 -j REDIRECT --to-port 8080
```

If you want to persist this across reboots, you can use the `iptables-persistent` package (see
[here](http://www.microhowto.info/howto/make_the_configuration_of_iptables_persistent_on_debian.html)).

### 4. Fire up mitmproxy.

You probably want a command like this:

```bash
mitmproxy --mode transparent --showhost
```

The `--mode transparent` option turns on transparent mode, and the `--showhost` argument tells
 mitmproxy to use the value of the Host header for URL display.

### 5. Finally, configure your test device.

Set the test device up to use the host on which mitmproxy is running as the default gateway and
[install the mitmproxy certificate authority on the test device]({{< relref "concepts-certificates" >}}).

### Work-around to redirect traffic originating from the machine itself

Follow steps **1, 2** as above, but *instead* of the commands in step **3**, run the following

Create a user to run the mitmproxy

```bash
sudo useradd --create-home mitmproxyuser
sudo -u mitmproxyuser -H bash -c 'cd ~ && pip install --user mitmproxy'
```

Then, configure the iptables rules to redirect all traffic from our local machine to mitmproxy. **Note**, as soon as you run these, you won't be able to perform successful network calls *until* you start mitmproxy. If you run into issues, `iptables -t nat -F` is a heavy handed way to flush (clear) *all* the rules from the iptables `nat` table (which includes any other rules you had configured).

```bash
iptables -t nat -A OUTPUT -p tcp -m owner ! --uid-owner mitmproxyuser --dport 80 -j REDIRECT --to-port 8080
iptables -t nat -A OUTPUT -p tcp -m owner ! --uid-owner mitmproxyuser --dport 443 -j REDIRECT --to-port 8080
ip6tables -t nat -A OUTPUT -p tcp -m owner ! --uid-owner mitmproxyuser --dport 80 -j REDIRECT --to-port 8080
ip6tables -t nat -A OUTPUT -p tcp -m owner ! --uid-owner mitmproxyuser --dport 443 -j REDIRECT --to-port 8080
```

This will redirect the packets from all users other than `mitmproxyuser` on the machine to mitmproxy. To avoid circularity, run mitmproxy as the user `mitmproxyuser`. Hence step **4** should look like:

```bash
sudo -u mitmproxyuser -H bash -c '$HOME/.local/bin/mitmproxy --mode transparent --showhost --set block_global=false'
```

## OpenBSD

### 1. Enable IP forwarding.

```bash
sudo sysctl -w net.inet.ip.forwarding=1
```

### 2. Place the following two lines in **/etc/pf.conf**.

```
mitm_if = "re2"
pass in quick proto tcp from $mitm_if to port { 80, 443 } divert-to 127.0.0.1 port 8080
```

These rules tell pf to divert all traffic from `$mitm_if` destined for port 80
or 443 to the local mitmproxy instance running on port 8080. You should replace
`$mitm_if` value with the interface on which your test device will appear.

### 3. Configure pf with the rules.

```bash
doas pfctl -f /etc/pf.conf
```

### 4. And now enable it.

```bash
doas pfctl -e
```

### 5. Fire up mitmproxy.

You probably want a command like this:

```bash
mitmproxy --mode transparent --listen-host 127.0.0.1 --showhost
```

The `--mode transparent` option turns on transparent mode, and the `--showhost` argument tells
mitmproxy to use the value of the Host header for URL display.

### 6. Finally, configure your test device.

Set the test device up to use the host on which mitmproxy is running as the default gateway and
[install the mitmproxy certificate authority on the test device]({{< relref "concepts-certificates" >}}).

{{% note %}}
Note that the **divert-to** rules in the pf.conf given above only apply
to inbound traffic. **This means that they will NOT redirect traffic
coming from the box running pf itself.** We can't distinguish between an
outbound connection from a non-mitmproxy app, and an outbound connection
from mitmproxy itself - if you want to intercept your traffic, you
should use an external host to run mitmproxy. Nonetheless, pf is
flexible to cater for a range of creative possibilities, like
intercepting traffic emanating from VMs. See the **pf.conf** man page
for more.
{{% /note %}}

## macOS

OSX Lion integrated the [pf](https://en.wikipedia.org/wiki/PF_(firewall))
packet filter from the OpenBSD project, which mitmproxy uses to implement
transparent mode on OSX. Note that this means we don't support transparent mode
for earlier versions of OSX.

### 1. Enable IP forwarding.

```bash
sudo sysctl -w net.inet.ip.forwarding=1
```

### 2. Place the following line in a file called, say, **pf.conf**.

```
rdr pass on en0 inet proto tcp to any port {80, 443} -> 127.0.0.1 port 8080
```

This rule tells pf to redirect all traffic destined for port 80 or 443
to the local mitmproxy instance running on port 8080. You should replace
`en0` with the interface on which your test device will appear.

### 3. Configure pf with the rules.

```bash
sudo pfctl -f pf.conf
```

### 4. And now enable it.

```bash
sudo pfctl -e
```

### 5. Configure sudoers to allow mitmproxy to access pfctl.

Edit the file **/etc/sudoers** on your system as root. Add the following line to
the end of the file:

```
ALL ALL=NOPASSWD: /sbin/pfctl -s state
```

Note that this allows any user on the system to run the command `/sbin/pfctl -s
state` as root without a password. This only allows inspection of the state
table, so should not be an undue security risk. If you're special feel free to
tighten the restriction up to the user running mitmproxy.

### 6. Fire up mitmproxy.

You probably want a command like this:

```bash
mitmproxy --mode transparent --showhost
```

The `--mode transparent` flag turns on transparent mode, and the `--showhost` argument tells
mitmproxy to use the value of the Host header for URL display.

### 7. Finally, configure your test device.

Set the test device up to use the host on which mitmproxy is running as the default gateway and
[install the mitmproxy certificate authority on the test device]({{< relref "concepts-certificates" >}}).

{{% note %}}
Note that the **rdr** rules in the pf.conf given above only apply to
inbound traffic. **This means that they will NOT redirect traffic coming
from the box running pf itself.** We can't distinguish between an
outbound connection from a non-mitmproxy app, and an outbound connection
from mitmproxy itself. If you want to intercept your own macOS traffic, see the work-around below or use an external host to run mitmproxy. In fact, PF is
flexible to cater for a range of creative possibilities, like
intercepting traffic emanating from VMs. See the **pf.conf** man page
for more.
{{% /note %}}

### Work-around to redirect traffic originating from the machine itself

Follow steps **1, 2** as above, but in step **2** change the contents of the file **pf.conf** to

```
#The ports to redirect to proxy
redir_ports = "{http, https}"

#The address the transparent proxy is listening on
tproxy = "127.0.0.1 port 8080"

#The user the transparent proxy is running as
tproxy_user = "nobody"

#The users whose connection must be redirected.
#
#This cannot involve the user which runs the
#transparent proxy as that would cause an infinite loop.
#

rdr pass proto tcp from any to any port $redir_ports -> $tproxy
pass out route-to (lo0 127.0.0.1) proto tcp from any to any port $redir_ports user { != $tproxy_user }
```

Follow steps **3-5** above. This will redirect the packets from all users other than `nobody` on the machine to mitmproxy. To avoid circularity, run mitmproxy as the user `nobody`. Hence step **6** should look like:

```bash
sudo -u nobody mitmproxy --mode transparent --showhost
```

## "Full" transparent mode on Linux

By default mitmproxy will use its own local IP address for its server-side
connections. In case this isn't desired, the --spoof-source-address argument can
be used to use the client's IP address for server-side connections. The
following config is required for this mode to work:

```bash
CLIENT_NET=192.168.1.0/24
TABLE_ID=100
MARK=1

echo "$TABLE_ID     mitmproxy" >> /etc/iproute2/rt_tables
iptables -t mangle -A PREROUTING -d $CLIENT_NET -j MARK --set-mark $MARK
iptables -t nat \
    -A PREROUTING -p tcp -s $CLIENT_NET \
    --match multiport --dports 80,443 -j \
    REDIRECT --to-port 8080

ip rule add fwmark $MARK lookup $TABLE_ID
ip route add local $CLIENT_NET dev lo table $TABLE_ID
```

This mode does require root privileges though. There's a wrapper in the examples
directory called 'mitmproxy_shim.c', which will enable you to use this mode with
dropped privileges. It can be used as follows:

```bash
gcc examples/complex/full_transparency_shim.c -o mitmproxy_shim -lcap
sudo chown root:root mitmproxy_shim
sudo chmod u+s mitmproxy_shim
./mitmproxy_shim $(which mitmproxy) --mode transparent --set spoof-source-address
```
