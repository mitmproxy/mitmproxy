.. _reverseproxy:

Reverse Proxy
=============

In reverse proxy mode, mitmproxy accepts standard HTTP(S) requests and forwards
them to the specified upstream server. This is in contrast to :ref:`upstreamproxy`, in which
mitmproxy forwards HTTP(S) proxy requests to an upstream proxy server.

================== ================================
command-line       ``-R http[s]://hostname[:port]``
================== ================================

Here, **http[s]** signifies if the proxy should use TLS to connect to the server.
mitmproxy always accepts both encrypted and unencrypted requests and transforms
them to what the server expects.

.. code-block:: none

    >>> mitmdump -R https://httpbin.org -p 80
    >>> curl http://localhost/
    # requests will be transparently upgraded to TLS by mitmproxy

    >>> mitmdump -R https://httpbin.org -p 443
    >>> curl https://localhost/
    # mitmproxy will use TLS on both ends.


Host Header
-----------

In reverse proxy mode, mitmproxy automatically rewrites the Host header to match the
upstream server. This allows mitmproxy to easily connect to existing endpoints on the
open web (e.g. ``mitmproxy -R https://example.com``).

However, keep in mind that absolute URLs within the returned document or HTTP redirects will
NOT be rewritten by mitmproxy. This means that if you click on a link for "http://example.com"
in the returned web page, you will be taken directly to that URL, bypassing mitmproxy.

One possible way to address this is to modify the hosts file of your OS so that "example.com"
resolves to your proxy's IP, and then access the proxy by going directly to example.com.
Make sure that your proxy can still resolve the original IP, or specify an IP in mitmproxy.