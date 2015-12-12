.. _upstreamcerts:

Upstream Certificates
=====================

When mitmproxy receives a connection destined for an SSL-protected service, it
freezes the connection before reading its request data, and makes a connection
to the upstream server to "sniff" the contents of its SSL certificate. The
information gained - the **Common Name** and **Subject Alternative Names** - is
then used to generate the interception certificate, which is sent to the client
so the connection can continue.

This rather intricate little dance lets us seamlessly generate correct
certificates even if the client has specified only an IP address rather than the
hostname. It also means that we don't need to sniff additional data to generate
certs in transparent mode.

Upstream cert sniffing is on by default, and can optionally be turned off.

================== =============================
command-line       :option:`--no-upstream-cert`
mitmproxy shortcut :kbd:`o` then :kbd:`U`
================== =============================
