"""
Experimental sans-io implementation of mitmproxy's protocol stack.

Most important primitives:
    - layers: represent protocol layers, e.g. one for tcp, tls, and so on. Layers are stacked, so
      a typical configuration might be ReverseProxy/TLS/TCP.
    - server: the proxy server does all IO and communication with the mitmproxy master.
      It creates the top layer for each incoming client connection.
    - events: When IO actions occur at the proxy server, they are passed down to the top layer as events.
    - commands: In the other direction, layers can emit commands to higher layers or the proxy server.
      This is used to e.g. send data, request for new connections to be opened, or to use mitmproxy's
      script hooks.
    - context: The context is the connection context each layer is provided with. This is still very
      much WIP, but this should expose stuff like Server Name Indication to lower layers.
"""
