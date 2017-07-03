.. _streaming:

HTTP Streaming
==============

By default, mitmproxy will read the entire request/response, perform any indicated
manipulations on it and then send the (possibly modified) message to
the other party. In some cases this is undesirable and you may wish to "stream"
the request/response. When streaming is enabled, the request/response is
not buffered on the proxy but directly sent to the server/client instead.
HTTP headers are still fully buffered before being sent.

Request Streaming
-----------------

Request streaming can be used to incrementally stream a request body to the server
before it has been fully received by the proxy. This is useful for large file uploads.

Response Streaming
------------------

By using mitmproxy's streaming feature, response contents can be passed to the client incrementally
before they have been fully received by the proxy. This is especially useful for large binary files
such as videos, where buffering the whole file slows down the client's browser.

On the command-line
-------------------

Streaming can be enabled on the command line for all request and response bodies exceeding a certain size.
The SIZE argument understands k/m/g suffixes, e.g. 3m for 3 megabytes.

================== =================
command-line       ``--set stream_large_bodies=SIZE``
================== =================

.. warning::

    When streaming is enabled, **streamed request/response contents will not be
    recorded or preserved in any way.**

.. note::

    When streaming is enabled, the request/response body cannot be modified by the usual means.

Customizing Streaming
---------------------

You can also use a script to customize exactly which requests or responses are streamed.

Requests/Responses that should be tagged for streaming by setting their ``.stream``
attribute to ``True``:

.. literalinclude:: ../../examples/complex/stream.py
   :caption: examples/complex/stream.py
   :language: python

Implementation Details
----------------------

When response streaming is enabled, portions of the code which would have otherwise performed
changes on the request/response body will see an empty body. Any modifications will be ignored.

Streamed bodies are usually sent in chunks of 4096 bytes. If the response is sent with a
``Transfer-Encoding: chunked`` header, the response will be streamed one chunk at a time.

Modifying streamed data
-----------------------

If the ``.stream`` attribute is callable, ``.stream`` will wrap the generator that yields all
chunks.

.. literalinclude:: ../../examples/complex/stream_modify.py
   :caption: examples/complex/stream_modify.py
   :language: python

WebSocket Streaming
===================

The WebSocket streaming feature can be used to send the frames as soon as they arrive. This can be useful for large binary file transfers.

On the command-line
-------------------

Streaming can be enabled on the command line for all WebSocket frames

================== =================
command-line       ``--set stream_websockets=true``
================== =================

.. note::

    When Web Socket streaming is enabled, the message payload cannot be modified.

Implementation Details
----------------------
When WebSocket streaming is enabled, portions of the code which may perform changes to the WebSocket message payloads will not have
any effect on the actual payload sent to the server as the frames are immediately forwarded to the server.
In contrast to HTTP streaming, where the body is not stored, the message payload will still be stored in the WebSocket Flow.

.. seealso::

    - :ref:`passthrough`
