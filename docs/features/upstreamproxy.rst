.. _upstreamproxy:

Upstream proxy mode
===================

In this mode, mitmproxy accepts proxy requests and unconditionally forwards all
requests to a specified upstream proxy server. This is in contrast to :ref:`reverseproxy`,
in which mitmproxy forwards ordinary HTTP requests to an upstream server.

================== ===================================
command-line       :option:`-U http://hostname[:port]`
================== ===================================
