.. _transparent:

====================
Transparent Proxying
====================

When a transparent proxy is used, traffic is redirected into a proxy at the
network layer, without any client configuration being required. This makes
transparent proxying ideal for those situations where you can't change client
behaviour - proxy-oblivious Android applications being a common example.

To set up transparent proxying, we need two new components. The first is a
redirection mechanism that transparently reroutes a TCP connection destined for
a server on the Internet to a listening proxy server. This usually takes the
form of a firewall on the same host as the proxy server - iptables_ on Linux
or pf_ on OSX. When the proxy receives a redirected connection, it sees a vanilla
HTTP request, without a host specification. This is where the second new component
comes in - a host module that allows us to query the redirector for the original
destination of the TCP connection.

At the moment, mitmproxy supports transparent proxying on OSX Lion and above,
and all current flavors of Linux.

Fully transparent mode
======================

By default mitmproxy will use its own local ip address for its server-side connections.
In case this isn't desired, the --spoof-source-address argument can be used to
use the client's ip address for server-side connections. The following config is
required for this mode to work:

    CLIENT_NET=192.168.1.0/24
    TABLE_ID=100
    MARK=1

    echo "$TABLE_ID     mitmproxy" >> /etc/iproute2/rt_tables
    iptables -t mangle -A PREROUTING -d $CLIENT_NET -j MARK --set-mark $MARK
    iptables -t nat -A PREROUTING -p tcp -s $CLIENT_NET --match multiport --dports 80,443 -j REDIRECT --to-port 8080

    ip rule add fwmark $MARK lookup $TABLE_ID
    ip route add local $CLIENT_NET dev lo table $TABLE_ID

This mode does require root privileges though. There's a wrapper in the examples directory
called 'mitmproxy_shim.c', which will enable you to use this mode with dropped priviliges.
It can be used as follows:

    gcc examples/mitmproxy_shim.c -o mitmproxy_shim -lcap
    sudo chown root:root mitmproxy_shim
    sudo chmod u+s mitmproxy_shim
    ./mitmproxy_shim $(which mitmproxy) -T --spoof-source-address

.. _iptables: http://www.netfilter.org/
.. _pf: https://en.wikipedia.org/wiki/PF_\(firewall\)
