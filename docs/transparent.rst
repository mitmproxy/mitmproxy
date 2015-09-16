.. _transparent:

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

.. _iptables: http://www.netfilter.org/
.. _pf: https://en.wikipedia.org/wiki/PF_\(firewall\)
