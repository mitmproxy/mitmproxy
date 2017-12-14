.. _http2_protocol:

HTTP/2
======

.. seealso::

    - `RFC7540: Hypertext Transfer Protocol Version 2 (HTTP/2) <http://tools.ietf.org/html/rfc7540>`_

HTTP/2 support in mitmproxy is based on the amazing work by the python-hyper
community with the `hyper-h2 <https://github.com/python-hyper/hyper-h2>`_
project. It fully encapsulates the internal state of HTTP/2 connections and
provides an easy-to-use event-based API.

mitmproxy currently does not support HTTP/2 trailers - but if you want to send
us a PR, we promise to take look!
