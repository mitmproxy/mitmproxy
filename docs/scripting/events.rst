.. _events:

Events
=======

General
-------

.. list-table::
    :widths: 40 60
    :header-rows: 0

    *   - .. py:function:: configure(options, updated)
        - Called once on startup, and whenever options change.

          *options*
            An ``options.Options`` object with the total current configuration
            state of mitmproxy.
          *updated*
            A set of strings indicating which configuration options have been
            updated. This contains all options when *configure* is called on
            startup, and only changed options subsequently.

    *   - .. py:function:: done()
        - Called once when the script shuts down, either because it's been
          unloaded, or because the proxy itself is shutting down.

    *   - .. py:function:: log(entry)
        - Called whenever an event log is added.

          *entry*
            An ``controller.LogEntry`` object - ``entry.msg`` is the log text,
            and ``entry.level`` is the urgency level ("debug", "info", "warn",
            "error").

    *   - .. py:function:: start()
        - Called once on startup, before any other events. If you return a
          value  from this event, it will replace the current addon. This
          allows you to, "boot into" an addon implemented as a class instance
          from the module level.

    *   - .. py:function:: tick()
        - Called at a regular sub-second interval as long as the addon is
          executing.


Connection
----------

.. list-table::
    :widths: 40 60
    :header-rows: 0

    *   - .. py:function:: clientconnect(root_layer)
        - Called when a client initiates a connection to the proxy. Note that a
          connection can correspond to multiple HTTP requests.

          *root_layer*
            The root layer (see `mitmproxy.proxy.protocol` for an explanation what
            the root layer is), provides transparent access to all attributes
            of the :py:class:`~mitmproxy.proxy.RootContext`. For example,
            ``root_layer.client_conn.address`` gives the remote address of the
            connecting client.

    *   - .. py:function:: clientdisconnect(root_layer)
        - Called when a client disconnects from the proxy.

          *root_layer*
            The root layer object.

    *   - .. py:function:: next_layer(layer)

        - Called whenever layers are switched. You may change which layer will
          be used by returning a new layer object from this event.

          *layer*
            The next layer, as determined by mitmpmroxy.

    *   - .. py:function:: serverconnect(server_conn)
        - Called before the proxy initiates a connection to the target server.
          Note that a connection can correspond to multiple HTTP requests.

          *server_conn*
            A ``ServerConnection`` object. It is guaranteed to have a non-None
            ``address`` attribute.

    *   - .. py:function:: serverdisconnect(server_conn)
        - Called when the proxy has closed the server connection.

          *server_conn*
            A ``ServerConnection`` object.


HTTP Events
-----------

.. list-table::
    :widths: 40 60
    :header-rows: 0

    *   - .. py:function:: http_connect(flow)
        - Called when we receive an HTTP CONNECT request. Setting a non 2xx
          response on the flow will return the response to the client and abort 
          the connection. CONNECT requests and responses do not generate the 
          usual HTTP handler events. CONNECT requests are only valid in regular 
          and upstream proxy modes.

          *flow*
            A ``models.HTTPFlow`` object. The flow is guaranteed to have
            non-None ``request``  and ``requestheaders`` attributes.


    *   - .. py:function:: request(flow)
        - Called when a client request has been received.

          *flow*
            A ``models.HTTPFlow`` object. At this point, the flow is
            guaranteed to have a non-None ``request`` attribute.

    *   - .. py:function:: requestheaders(flow)
        - Called when the headers of a client request have been received, but
          before the request body is read.

          *flow*
            A ``models.HTTPFlow`` object. At this point, the flow is
            guaranteed to have a non-None ``request`` attribute.

    *   - .. py:function:: responseheaders(flow)

        - Called when the headers of a server response have been received, but
          before the response body is read.

          *flow*
            A ``models.HTTPFlow`` object. At this point, the flow is
            guaranteed to have a non-none ``request`` and ``response``
            attributes, however the response will have no content.

    *   - .. py:function:: response(flow)

        - Called when a server response has been received.

          *flow*
            A ``models.HTTPFlow`` object. At this point, the flow is
            guaranteed to have a non-none ``request`` and ``response``
            attributes. The raw response body will be in ``response.body``,
            unless response streaming has been enabled.

    *   - .. py:function:: error(flow)
        - Called when a flow error has occurred, e.g. invalid server responses,
          or interrupted connections. This is distinct from a valid server HTTP
          error response, which is simply a response with an HTTP error code.

          *flow*
            The flow containing the error. It is guaranteed to have
            non-None ``error`` attribute.


WebSocket Events
-----------------

These events are called only after a connection made an HTTP upgrade with
"101 Switching Protocols". No further HTTP-related events after the handshake
are issued, only new WebSocket messages are called.

.. list-table::
    :widths: 40 60
    :header-rows: 0

    *   - .. py:function:: websocket_handshake(flow)
        - Called when a client wants to establish a WebSocket connection. The
          WebSocket-specific headers can be manipulated to alter the
          handshake. The ``flow`` object is guaranteed to have a non-None
          ``request`` attribute.

          *flow*
            The flow containing the HTTP WebSocket handshake request. The
            object is guaranteed to have a non-None ``request`` attribute.

    *   - .. py:function:: websocket_start(flow)
        - Called when WebSocket connection is established after a successful
          handshake.

          *flow*
            A ``models.WebSocketFlow`` object.

    *   - .. py:function:: websocket_message(flow)

        - Called when a WebSocket message is received from the client or server. The
          sender and receiver are identifiable. The most recent message will be
          ``flow.messages[-1]``. The message is user-modifiable and is killable.
          A message is either of TEXT or BINARY type.

          *flow*
            A ``models.WebSocketFlow`` object.

    *   - .. py:function:: websocket_end(flow)
        - Called when WebSocket connection ends.

          *flow*
            A ``models.WebSocketFlow`` object.

    *   - .. py:function:: websocket_error(flow)
        - Called when a WebSocket error occurs - e.g. the connection closing
          unexpectedly.

          *flow*
            A ``models.WebSocketFlow`` object.


TCP Events
----------

These events are called only if the connection is in :ref:`TCP mode
<tcp_proxy>`. So, for instance, TCP events are not called for ordinary HTTP/S
connections.

.. list-table::
    :widths: 40 60
    :header-rows: 0


    *   - .. py:function:: tcp_start(flow)
        - Called when TCP streaming starts.

          *flow*
            A ``models.TCPFlow`` object.

    *   - .. py:function:: tcp_message(flow)

        - Called when a TCP payload is received from the client or server. The
          sender and receiver are identifiable. The most recent message will be
          ``flow.messages[-1]``. The message is user-modifiable.

          *flow*
            A ``models.TCPFlow`` object.

    *   - .. py:function:: tcp_end(flow)
        - Called when TCP streaming ends.

          *flow*
            A ``models.TCPFlow`` object.

    *   - .. py:function:: tcp_error(flow)
        - Called when a TCP error occurs - e.g. the connection closing
          unexpectedly.

          *flow*
            A ``models.TCPFlow`` object.
