"""
mitmproxy protocol architecture

In mitmproxy, protocols are implemented as a set of layers, which are composed on top each other.
For example, the following scenarios depict possible settings (lowest layer first):

Transparent HTTP proxy, no SSL:
    TransparentProxy
    Http1Layer
    HttpLayer

Regular proxy, CONNECT request with WebSockets over SSL:
    HttpProxy
    Http1Layer
    HttpLayer
    SslLayer
    WebsocketLayer (or TcpLayer)

Automated protocol detection by peeking into the buffer:
    TransparentProxy
    TLSLayer
    Http2Layer
    HttpLayer

Communication between layers is done as follows:
    - lower layers provide context information to higher layers
    - higher layers can call functions provided by lower layers,
      which are propagated until they reach a suitable layer.

Further goals:
  - Connections should always be peekable to make automatic protocol detection work.
  - Upstream connections should be established as late as possible;
    inline scripts shall have a chance to handle everything locally.
"""
from __future__ import (absolute_import, print_function, division)
from netlib import tcp
from ..models import ServerConnection
from ..exceptions import ProtocolException


class _LayerCodeCompletion(object):
    """
    Dummy class that provides type hinting in PyCharm, which simplifies development a lot.
    """

    def __init__(self, *args, **kwargs):  # pragma: nocover
        super(_LayerCodeCompletion, self).__init__(*args, **kwargs)
        if True:
            return
        self.config = None
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = None
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.channel = None
        """@type: libmproxy.controller.Channel"""


class Layer(_LayerCodeCompletion):
    def __init__(self, ctx, *args, **kwargs):
        """
        Args:
            ctx: The (read-only) higher layer.
        """
        self.ctx = ctx
        super(Layer, self).__init__(*args, **kwargs)

    def __call__(self):
        """
        Logic of the layer.
        Raises:
            ProtocolException in case of protocol exceptions.
        """
        raise NotImplementedError()

    def __getattr__(self, name):
        """
        Attributes not present on the current layer may exist on a higher layer.
        """
        return getattr(self.ctx, name)

    def log(self, msg, level, subs=()):
        full_msg = [
            "{}: {}".format(repr(self.client_conn.address), msg)
        ]
        for i in subs:
            full_msg.append("  -> " + i)
        full_msg = "\n".join(full_msg)
        self.channel.tell("log", Log(full_msg, level))

    @property
    def layers(self):
        return [self] + self.ctx.layers

    def __repr__(self):
        return type(self).__name__


class ServerConnectionMixin(object):
    """
    Mixin that provides a layer with the capabilities to manage a server connection.
    """

    def __init__(self, server_address=None):
        super(ServerConnectionMixin, self).__init__()
        self.server_conn = ServerConnection(server_address)
        self._check_self_connect()

    def reconnect(self):
        address = self.server_conn.address
        self._disconnect()
        self.server_conn.address = address
        self.connect()

    def _check_self_connect(self):
        """
        We try to protect the proxy from _accidentally_ connecting to itself,
        e.g. because of a failed transparent lookup or an invalid configuration.
        """
        address = self.server_conn.address
        if address:
            self_connect = (
                address.port == self.config.port and
                address.host in ("localhost", "127.0.0.1", "::1")
            )
            if self_connect:
                raise ProtocolException(
                    "Invalid server address: {}\r\n"
                    "The proxy shall not connect to itself.".format(repr(address))
                )

    def set_server(self, address, server_tls=None, sni=None, depth=1):
        if depth == 1:
            if self.server_conn:
                self._disconnect()
            self.log("Set new server address: " + repr(address), "debug")
            self.server_conn.address = address
            self._check_self_connect()
            if server_tls:
                raise ProtocolException(
                    "Cannot upgrade to TLS, no TLS layer on the protocol stack."
                )
        else:
            self.ctx.set_server(address, server_tls, sni, depth - 1)

    def _disconnect(self):
        """
        Deletes (and closes) an existing server connection.
        """
        self.log("serverdisconnect", "debug", [repr(self.server_conn.address)])
        self.server_conn.finish()
        self.server_conn.close()
        # self.channel.tell("serverdisconnect", self)
        self.server_conn = ServerConnection(None)

    def connect(self):
        if not self.server_conn.address:
            raise ProtocolException("Cannot connect to server, no server address given.")
        self.log("serverconnect", "debug", [repr(self.server_conn.address)])
        try:
            self.server_conn.connect()
        except tcp.NetLibError as e:
            raise ProtocolException(
                "Server connection to %s failed: %s" % (repr(self.server_conn.address), e), e)


class Log(object):
    def __init__(self, msg, level="info"):
        self.msg = msg
        self.level = level


class Kill(Exception):
    """
    Kill a connection.
    """
