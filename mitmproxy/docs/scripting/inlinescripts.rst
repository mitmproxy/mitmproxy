.. _inlinescripts:

Inline Scripts
==============

**mitmproxy** has a powerful scripting API that allows you to modify flows
on-the-fly or rewrite previously saved flows locally.

The mitmproxy scripting API is event driven - a script is simply a Python
module that exposes a set of event methods. Here's a complete mitmproxy script
that adds a new header to every HTTP response before it is returned to the
client:

.. literalinclude:: ../../examples/add_header.py
   :caption: examples/add_header.py
   :language: python

The first argument to each event method is an instance of
:py:class:`~mitmproxy.script.ScriptContext` that lets the script interact with the global mitmproxy
state. The **response** event also gets an instance of :py:class:`~mitmproxy.script.ScriptContext`,
which we can use to manipulate the response itself.

We can now run this script using mitmdump or mitmproxy as follows:

>>> mitmdump -s add_header.py

The new header will be added to all responses passing through the proxy.

Examples
--------

mitmproxy comes with a variety of example inline scripts, which demonstrate many basic tasks.
We encourage you to either browse them locally or on `GitHub`_.


Events
------

The ``context`` argument passed to each event method is always a
:py:class:`~mitmproxy.script.ScriptContext` instance. It is guaranteed to be the same object
for the scripts lifetime and is not shared between multiple inline scripts. You can safely use it
to store any form of state you require.

Script Lifecycle Events
^^^^^^^^^^^^^^^^^^^^^^^

.. py:function:: start(context, argv)

    Called once on startup, before any other events.

    :param List[str] argv: The inline scripts' arguments.
        For example, ``mitmproxy -s 'example.py --foo 42'`` sets argv to ``["--foo", "42"]``.

.. py:function:: done(context)

    Called once on script shutdown, after any other events.

Connection Events
^^^^^^^^^^^^^^^^^

.. py:function:: clientconnect(context, root_layer)

    Called when a client initiates a connection to the proxy. Note that
    a connection can correspond to multiple HTTP requests.

    .. versionchanged:: 0.14

    :param Layer root_layer: The root layer (see :ref:`protocols` for an explanation what the root
        layer is), which provides transparent access to all attributes of the
        :py:class:`~mitmproxy.proxy.RootContext`. For example, ``root_layer.client_conn.address``
        gives the remote address of the connecting client.

.. py:function:: clientdisconnect(context, root_layer)

    Called when a client disconnects from the proxy.

    .. versionchanged:: 0.14

    :param Layer root_layer: see :py:func:`clientconnect`

.. py:function:: serverconnect(context, server_conn)

    Called before the proxy initiates a connection to the target server. Note that
    a connection can correspond to multiple HTTP requests.

    :param ServerConnection server_conn: The server connection object. It is guaranteed to have a
        non-None ``address`` attribute.

.. py:function:: serverdisconnect(context, server_conn)

    Called when the proxy has closed the server connection.

    .. versionadded:: 0.14

    :param ServerConnection server_conn: see :py:func:`serverconnect`

HTTP Events
^^^^^^^^^^^

.. py:function:: request(context, flow)

    Called when a client request has been received. The ``flow`` object is
    guaranteed to have a non-None ``request`` attribute.

    :param HTTPFlow flow: The flow containing the request which has been received.
        The object is guaranteed to have a non-None ``request`` attribute.

.. py:function:: responseheaders(context, flow)

    Called when the headers of a server response have been received.
    This will always be called before the response hook.

    :param HTTPFlow flow: The flow containing the request and response.
        The object is guaranteed to have non-None ``request`` and
        ``response`` attributes. ``response.content`` will be ``None``,
        as the response body has not been read yet.

.. py:function:: response(context, flow)

    Called when a server response has been received.

    :param HTTPFlow flow: The flow containing the request and response.
        The object is guaranteed to have non-None ``request`` and
        ``response`` attributes. ``response.body`` will contain the raw response body,
        unless response streaming has been enabled.

.. py:function:: error(context, flow)

    Called when a flow error has occurred, e.g. invalid server responses, or
    interrupted connections. This is distinct from a valid server HTTP error
    response, which is simply a response with an HTTP error code.

    :param HTTPFlow flow: The flow containing the error.
        It is guaranteed to have non-None ``error`` attribute.

TCP Events
^^^^^^^^^^

.. py:function:: tcp_message(context, tcp_msg)

    .. warning::  API is subject to change

    If the proxy is in :ref:`TCP mode <tcpproxy>`, this event is called when it
    receives a TCP payload from the client or server.

    The sender and receiver are identifiable. The message is user-modifiable.

    :param TcpMessage tcp_msg: see *examples/tcp_message.py*

API
---

The canonical API documentation is the code, which you can browse here, locally or on `GitHub`_.
*Use the Source, Luke!*

The main classes you will deal with in writing mitmproxy scripts are:

:py:class:`~mitmproxy.script.ScriptContext`
    - A handle for interacting with mitmproxy's Flow Master from within scripts.
:py:class:`~mitmproxy.models.ClientConnection`
    - Describes a client connection.
:py:class:`~mitmproxy.models.ServerConnection`
    - Describes a server connection.
:py:class:`~mitmproxy.models.HTTPFlow`
    - A collection of objects representing a single HTTP transaction.
:py:class:`~mitmproxy.models.HTTPRequest`
    - An HTTP request.
:py:class:`~mitmproxy.models.HTTPResponse`
    - An HTTP response.
:py:class:`~mitmproxy.models.Error`
    - A communications error.
:py:class:`netlib.http.Headers`
    - A dictionary-like object for managing HTTP headers.
:py:class:`netlib.certutils.SSLCert`
    - Exposes information SSL certificates.
:py:class:`mitmproxy.flow.FlowMaster`
    - The "heart" of mitmproxy, usually subclassed as :py:class:`mitmproxy.dump.DumpMaster` or
      :py:class:`mitmproxy.console.ConsoleMaster`.

Script Context
--------------

.. autoclass:: mitmproxy.script.ScriptContext
    :members:
    :undoc-members:

Running scripts in parallel
---------------------------

We have a single flow primitive, so when a script is blocking, other requests are not processed.
While that's usually a very desirable behaviour, blocking scripts can be run threaded by using the
:py:obj:`mitmproxy.script.concurrent` decorator.
**If your script does not block, you should avoid the overhead of the decorator.**

.. literalinclude:: ../../examples/nonblocking.py
   :caption: examples/nonblocking.py
   :language: python

Make scripts configurable with arguments
----------------------------------------

Sometimes, you want to pass runtime arguments to the inline script. This can be simply done by
surrounding the script call with quotes, e.g. ```mitmdump -s 'script.py --foo 42'``.
The arguments are then exposed in the start event:

.. literalinclude:: ../../examples/modify_response_body.py
   :caption: examples/modify_response_body.py
   :language: python

Running scripts on saved flows
------------------------------

Sometimes, we want to run a script on :py:class:`~mitmproxy.models.Flow` objects that are already
complete.  This happens when you start a script, and then load a saved set of flows from a file
(see the "scripted data transformation" example `here <https://mitmproxy.org/doc/mitmdump.html>`_).
It also happens when you run a one-shot script on a single flow through the ``|`` (pipe) shortcut
in mitmproxy.

In this case, there are no client connections, and the events are run in the following order:
**start**, **request**, **responseheaders**, **response**, **error**, **done**.
If the flow doesn't have a **response** or **error** associated with it, the matching events will
be skipped.

Spaces in the script path
-------------------------

By default, spaces are interpreted as a separator between the inline script and its arguments
(e.g. ``-s 'foo.py 42'``). Consequently, the script path needs to be wrapped in a separate pair of
quotes if it contains spaces: ``-s '\'./foo bar/baz.py\' 42'``.

.. _GitHub: https://github.com/mitmproxy/mitmproxy
