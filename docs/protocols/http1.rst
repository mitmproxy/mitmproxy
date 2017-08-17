.. _http1_protocol:

HTTP/1.0 and HTTP/1.1
===========================

.. seealso::

    - `RFC7230: HTTP/1.1: Message Syntax and Routing <http://tools.ietf.org/html/rfc7230>`_
    - `RFC7231: HTTP/1.1: Semantics and Content <http://tools.ietf.org/html/rfc7231>`_

HTTP/1.0 and HTTP/1.1 support in mitmproxy is based on our custom HTTP stack,
which takes care of all semantics and on-the-wire parsing/serialization tasks.

mitmproxy currently does not support HTTP trailers - but if you want to send
us a PR, we promise to take look!
