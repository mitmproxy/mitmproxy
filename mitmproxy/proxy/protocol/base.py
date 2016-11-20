from mitmproxy import exceptions
from mitmproxy import connections


class _LayerCodeCompletion:

    """
    Dummy class that provides type hinting in PyCharm, which simplifies development a lot.
    """

    def __init__(self, **mixin_args):  # pragma: no cover
        super().__init__(**mixin_args)
        if True:
            return
        self.config = None
        """@type: mitmproxy.proxy.ProxyConfig"""
        self.client_conn = None
        """@type: mitmproxy.connections.ClientConnection"""
        self.server_conn = None
        """@type: mitmproxy.connections.ServerConnection"""
        self.channel = None
        """@type: mitmproxy.controller.Channel"""
        self.ctx = None
        """@type: mitmproxy.proxy.protocol.Layer"""


class Layer(_LayerCodeCompletion):

    """
    Base class for all layers. All other protocol layers should inherit from this class.
    """

    def __init__(self, ctx, **mixin_args):
        """
        Each layer usually passes itself to its child layers as a context. Properties of the
        context are transparently mapped to the layer, so that the following works:

        .. code-block:: python

            root_layer = Layer(None)
            root_layer.client_conn = 42
            sub_layer = Layer(root_layer)
            print(sub_layer.client_conn) # 42

        The root layer is passed a :py:class:`mitmproxy.proxy.RootContext` object,
        which provides access to :py:attr:`.client_conn <mitmproxy.proxy.RootContext.client_conn>`,
        :py:attr:`.next_layer <mitmproxy.proxy.RootContext.next_layer>` and other basic attributes.

        Args:
            ctx: The (read-only) parent layer / context.
        """
        self.ctx = ctx
        """
        The parent layer.

        :type: :py:class:`Layer`
        """
        super().__init__(**mixin_args)

    def __call__(self):
        """Logic of the layer.

        Returns:
            Once the protocol has finished without exceptions.

        Raises:
            ~mitmproxy.exceptions.ProtocolException: if an exception occurs. No other exceptions must be raised.
        """
        raise NotImplementedError()

    def __getattr__(self, name):
        """
        Attributes not present on the current layer are looked up on the context.
        """
        return getattr(self.ctx, name)

    @property
    def layers(self):
        """
        List of all layers, including the current layer (``[self, self.ctx, self.ctx.ctx, ...]``)
        """
        return [self] + self.ctx.layers

    def __repr__(self):
        return type(self).__name__


class ServerConnectionMixin:

    """
    Mixin that provides a layer with the capabilities to manage a server connection.
    The server address can be passed in the constructor or set by calling :py:meth:`set_server`.
    Subclasses are responsible for calling :py:meth:`disconnect` before returning.

    Recommended Usage:

    .. code-block:: python

        class MyLayer(Layer, ServerConnectionMixin):
            def __call__(self):
                try:
                    # Do something.
                finally:
                    if self.server_conn.connected():
                        self.disconnect()
    """

    def __init__(self, server_address=None):
        super().__init__()

        self.server_conn = None
        if self.config.options.spoof_source_address and self.config.options.upstream_bind_address == '':
            self.server_conn = connections.ServerConnection(
                server_address, (self.ctx.client_conn.address.host, 0), True)
        else:
            self.server_conn = connections.ServerConnection(
                server_address, (self.config.options.upstream_bind_address, 0),
                self.config.options.spoof_source_address
            )

        self.__check_self_connect()

    def __check_self_connect(self):
        """
        We try to protect the proxy from _accidentally_ connecting to itself,
        e.g. because of a failed transparent lookup or an invalid configuration.
        """
        address = self.server_conn.address
        if address:
            self_connect = (
                address.port == self.config.options.listen_port and
                address.host in ("localhost", "127.0.0.1", "::1")
            )
            if self_connect:
                raise exceptions.ProtocolException(
                    "Invalid server address: {}\r\n"
                    "The proxy shall not connect to itself.".format(repr(address))
                )

    def set_server(self, address):
        """
        Sets a new server address. If there is an existing connection, it will be closed.
        """
        if self.server_conn.connected():
            self.disconnect()
        self.log("Set new server address: " + repr(address), "debug")
        self.server_conn.address = address
        self.__check_self_connect()

    def disconnect(self):
        """
        Deletes (and closes) an existing server connection.
        Must not be called if there is no existing connection.
        """
        self.log("serverdisconnect", "debug", [repr(self.server_conn.address)])
        address = self.server_conn.address
        self.server_conn.finish()
        self.server_conn.close()
        self.channel.tell("serverdisconnect", self.server_conn)

        self.server_conn = connections.ServerConnection(
            address,
            (self.server_conn.source_address.host, 0),
            self.config.options.spoof_source_address
        )

    def connect(self):
        """
        Establishes a server connection.
        Must not be called if there is an existing connection.

        Raises:
            ~mitmproxy.exceptions.ProtocolException: if the connection could not be established.
        """
        if not self.server_conn.address:
            raise exceptions.ProtocolException("Cannot connect to server, no server address given.")
        self.log("serverconnect", "debug", [repr(self.server_conn.address)])
        self.channel.ask("serverconnect", self.server_conn)
        try:
            self.server_conn.connect()
        except exceptions.TcpException as e:
            raise exceptions.ProtocolException(
                "Server connection to {} failed: {}".format(
                    repr(self.server_conn.address), str(e)
                )
            )
