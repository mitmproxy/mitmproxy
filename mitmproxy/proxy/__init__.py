"""
This module contains mitmproxy's core network proxy.

The most important primitives are:

    - Layers: represent protocol layers, e.g. one for TCP, TLS, and so on. Layers are nested, so
      a typical configuration might be ReverseProxy/TLS/TCP.
      Most importantly, layers are implemented using the sans-io pattern (https://sans-io.readthedocs.io/).
      This means that calls return immediately, there is no blocking sync or async code.
    - Server: the proxy server handles all I/O. This is implemented using `asyncio`, but could be done any other way.
      The `ConnectionHandler` is subclassed in the `Proxyserver` addon, which handles the communication with the
      rest of mitmproxy.
    - Events: When I/O actions occur at the proxy server, they are passed to the outermost layer as events,
      e.g. `DataReceived` or `ConnectionClosed`.
    - Commands: In the other direction, layers can emit commands to higher layers or the proxy server.
      This is used to e.g. send data, request for new connections to be opened, or to call mitmproxy's
      event hooks.
    - Context: The context is the connection context each layer is provided with, which is always a client connection
      and sometimes also a server connection.
"""
