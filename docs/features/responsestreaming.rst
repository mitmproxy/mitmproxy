.. _responsestreaming:

Response Streaming
==================

By using mitmproxy's streaming feature, response contents can be passed to the client incrementally
before they have been fully received by the proxy. This is especially useful for large binary files
such as videos, where buffering the whole file slows down the client's browser.

By default, mitmproxy will read the entire response, perform any indicated
manipulations on it and then send the (possibly modified) response to
the client. In some cases this is undesirable and you may wish to "stream"
the response back to the client. When streaming is enabled, the response is
not buffered on the proxy but directly sent back to the client instead.

On the command-line
-------------------

Streaming can be enabled on the command line for all response bodies exceeding a certain size.
The SIZE argument understands k/m/g suffixes, e.g. 3m for 3 megabytes.

================== =============================
command-line       :option:`--stream SIZE`
================== =============================

.. warning::

    When response streaming is enabled, **streamed response contents will not be
    recorded or preserved in any way.**

.. note::

    When response streaming is enabled, the response body cannot be modified by the usual means.

Customizing Response Streaming
------------------------------

You can also use an :ref:`inlinescripts` to customize exactly
which responses are streamed.

Responses that should be tagged for streaming by setting their ``.stream`` attribute to ``True``:

.. literalinclude:: ../../examples/stream.py
   :caption: examples/stream.py
   :language: python

Implementation Details
----------------------

When response streaming is enabled, portions of the code which would have otherwise performed
changes on the response body will see an empty response body. Any modifications will be ignored.

Streamed responses are usually sent in chunks of 4096 bytes. If the response is sent with a
``Transfer-Encoding: chunked`` header, the response will be streamed one chunk at a time.

Modifying streamed data
-----------------------

If the ``.stream`` attribute is callable, ``.stream`` will wrap the generator that yields all
chunks.

.. literalinclude:: ../../examples/stream_modify.py
   :caption: examples/stream_modify.py
   :language: python

.. seealso::

    - :ref:`passthrough`
