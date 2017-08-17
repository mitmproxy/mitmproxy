.. _websocket_protocol:

WebSocket
=========

.. seealso::

    - `RFC6455: The WebSocket Protocol <http://tools.ietf.org/html/rfc6455>`_
    - `RFC7692: Compression Extensions for WebSocket <http://tools.ietf.org/html/rfc7692>`_

WebSocket support in mitmproxy is based on the amazing work by the python-hyper
community with the `wsproto <https://github.com/python-hyper/wsproto>`_
project. It fully encapsulates WebSocket frames/messages/connections and
provides an easy-to-use event-based API.

mitmproxy fully supports the compression extension for WebSocket messages,
provided by wsproto.
