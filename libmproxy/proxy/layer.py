from __future__ import (absolute_import, print_function, division, unicode_literals)
from libmproxy.protocol.tcp import TCPHandler
from libmproxy.proxy.connection import ServerConnection
from netlib import tcp
from .primitives import Socks5ProxyMode, ProxyError, Log
from .message import Connect, Reconnect, ChangeServer


"""
mitmproxy protocol architecture

In mitmproxy, protocols are implemented as a set of layers, which are composed on top each other.
For example, the following scenarios depict possible scenarios (lowest layer first):

Transparent HTTP proxy, no SSL:
    TransparentModeLayer
    HttpLayer

Regular proxy, CONNECT request with WebSockets over SSL:
    RegularModeLayer
    HttpLayer
    SslLayer
    WebsocketLayer (or TcpLayer)

Automated protocol detection by peeking into the buffer:
    TransparentModeLayer
    AutoLayer
    SslLayer
    AutoLayer
    Http2Layer

Communication between layers is done as follows:
    - lower layers provide context information to higher layers
    - higher layers can "yield" commands to lower layers,
      which are propagated until they reach a suitable layer.

Further goals:
  - Connections should always be peekable to make automatic protocol detection work.
  - Upstream connections should be established as late as possible;
    inline scripts shall have a chance to handle everything locally.
"""


class ProxyError2(Exception):
    def __init__(self, message, cause=None):
        super(ProxyError2, self).__init__(message)
        self.cause = cause


class RootContext(object):
    """
    The outmost context provided to the root layer.
    As a consequence, every layer has .client_conn, .channel and .config.
    """

    def __init__(self, client_conn, config, channel):
        self.client_conn = client_conn  # Client Connection
        self.channel = channel  # provides .ask() method to communicate with FlowMaster
        self.config = config  # Proxy Configuration

    def __getattr__(self, name):
        """
        Accessing a nonexisting attribute does not throw an error but returns None instead.
        """
        return None


class LayerCodeCompletion(object):
    """
    Dummy class that provides type hinting in PyCharm, which simplifies development a lot.
    """
    def __init__(self):
        if True:
            return
        self.config = None
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = None
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.channel = None
        """@type: libmproxy.controller.Channel"""


class Layer(LayerCodeCompletion):
    def __init__(self, ctx):
        """
        Args:
            ctx: The (read-only) higher layer.
        """
        super(Layer, self).__init__()
        self.ctx = ctx

    def __call__(self):
        """
        Logic of the layer.
        Raises:
            ProxyError2 in case of protocol exceptions.
        """
        raise NotImplementedError

    def __getattr__(self, name):
        """
        Attributes not present on the current layer may exist on a higher layer.
        """
        return getattr(self.ctx, name)

    def log(self, msg, level, subs=()):
        full_msg = [
            "%s:%s: %s" %
            (self.client_conn.address.host,
             self.client_conn.address.port,
             msg)]
        for i in subs:
            full_msg.append("  -> " + i)
        full_msg = "\n".join(full_msg)
        self.channel.tell("log", Log(full_msg, level))


class _ServerConnectionMixin(object):
    def __init__(self):
        self._server_address = None
        self.server_conn = None

    def _handle_message(self, message):
        if message == Reconnect:
            self._disconnect()
            self._connect()
            return True
        elif message == Connect:
            self._connect()
            return True
        elif message == ChangeServer:
            raise NotImplementedError
        return False

    def _disconnect(self):
        """
        Deletes (and closes) an existing server connection.
        """
        self.log("serverdisconnect", "debug", [repr(self.server_conn.address)])
        self.server_conn.finish()
        self.server_conn.close()
        # self.channel.tell("serverdisconnect", self)
        self.server_conn = None

    def _connect(self):
        self.log("serverconnect", "debug", [repr(self.server_conn.address)])
        try:
            self.server_conn.connect()
        except tcp.NetLibError as e:
            raise ProxyError2("Server connection to '%s' failed: %s" % (self._server_address, repr(e)), e)

    def _set_address(self, address):
        a = tcp.Address.wrap(address)
        self.log("Set new server address: " + repr(a), "debug")
        self.server_conn = ServerConnection(a)


class Socks5IncomingLayer(Layer, _ServerConnectionMixin):
    def __call__(self):
        try:
            s5mode = Socks5ProxyMode(self.config.ssl_ports)
            address = s5mode.get_upstream_server(self.client_conn)[2:]
        except ProxyError as e:
            raise ProxyError2(str(e), e)

        self._set_address(address)

        layer = TcpLayer(self)
        for message in layer():
            if not self._handle_message(message):
                yield message


class TcpLayer(Layer):
    def __call__(self):
        yield Connect()
        tcp_handler = TCPHandler(self)
        tcp_handler.handle_messages()

    def establish_server_connection(self):
        print("establish server conn called")