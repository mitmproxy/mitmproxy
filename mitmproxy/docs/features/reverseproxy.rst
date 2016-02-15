.. _reverseproxy:

Reverse Proxy
=============

In reverse proxy mode, mitmproxy accepts standard HTTP(S) requests and forwards
them to the specified upstream server. This is in contrast to :ref:`upstreamproxy`, in which
mitmproxy forwards HTTP(S) proxy requests to an upstream proxy server.

================== =====================================
command-line       :option:`-R http[s]://hostname[:port]`
================== =====================================

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

In reverse proxy mode, mitmproxy does not rewrite the host header. While often useful, this
may lead to issues with public web servers. For example, consider the following scenario:

.. code-block:: none
    :emphasize-lines: 5

    >>> mitmdump -d -R http://example.com/
    >>> curl http://localhost:8080/

    >> GET https://example.com/
        Host: localhost:8080
        User-Agent: curl/7.35.0
        [...]

    << 404 Not Found 345B

Since the Host header doesn't match "example.com", an error is returned.
There are two ways to solve this:

1. Modify the hosts file of your OS so that "example.com" resolves to your proxy's IP.
   Then, access example.com directly. Make sure that your proxy can still resolve the original IP
   or specify an IP in mitmproxy.
2. Use mitmproxy's :ref:`setheaders` feature to rewrite the host header:
   ``--setheader :~q:Host:example.com``.
   However, keep in mind that absolute URLs within the returned document or HTTP redirects will
   cause the client application to bypass the proxy.
