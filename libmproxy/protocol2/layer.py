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
    SslLayer
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
from __future__ import (absolute_import, print_function, division)
import Queue
import threading
from netlib import tcp
from ..proxy import Log
from ..proxy.connection import ServerConnection
from .messages import Connect, Reconnect, SetServer, Kill
from ..exceptions import ProtocolException


class _LayerCodeCompletion(object):
    """
    Dummy class that provides type hinting in PyCharm, which simplifies development a lot.
    """

    def __init__(self):
        super(_LayerCodeCompletion, self).__init__()
        if True:
            return
        self.config = None
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = None
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.channel = None
        """@type: libmproxy.controller.Channel"""


class Layer(_LayerCodeCompletion):
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

    @property
    def layers(self):
        return [self] + self.ctx.layers

    def __repr__(self):
        return type(self).__name__


class ServerConnectionMixin(object):
    """
    Mixin that provides a layer with the capabilities to manage a server connection.
    """

    def __init__(self):
        super(ServerConnectionMixin, self).__init__()
        self._server_address = None
        self.server_conn = None

    def _handle_server_message(self, message):
        if message == Reconnect:
            self._disconnect()
            self._connect()
            return True
        elif message == Connect:
            self._connect()
            return True
        elif message == SetServer and message.depth == 1:
            if self.server_conn:
                self._disconnect()
            self.server_address = message.address
            return True
        elif message == Kill:
            self._disconnect()

        return False

    @property
    def server_address(self):
        return self._server_address

    @server_address.setter
    def server_address(self, address):
        self._server_address = tcp.Address.wrap(address)
        self.log("Set new server address: " + repr(self.server_address), "debug")

    def _disconnect(self):
        """
        Deletes (and closes) an existing server connection.
        """
        self.log("serverdisconnect", "debug", [repr(self.server_address)])
        self.server_conn.finish()
        self.server_conn.close()
        # self.channel.tell("serverdisconnect", self)
        self.server_conn = None

    def _connect(self):
        if not self.server_address:
            raise ProtocolException("Cannot connect to server, no server address given.")
        self.log("serverconnect", "debug", [repr(self.server_address)])
        self.server_conn = ServerConnection(self.server_address)
        try:
            self.server_conn.connect()
        except tcp.NetLibError as e:
            raise ProtocolException("Server connection to '%s' failed: %s" % (self.server_address, e), e)


def yield_from_callback(fun):
    """
    Decorator which makes it possible to yield from callbacks in the original thread.
    As a use case, take the pyOpenSSL handle_sni callback: If we receive a new SNI from the client,
    we need to reconnect to the server with the new SNI. Reconnecting would normally be done using "yield Reconnect()",
    but we're in a pyOpenSSL callback here, outside of the main program flow. With this decorator, it looks as follows:

    def handle_sni(self):
        # ...
        self.yield_from_callback(Reconnect())

    @yield_from_callback
    def establish_ssl_with_client():
        self.client_conn.convert_to_ssl(...)

    for message in self.establish_ssl_with_client():  # will yield Reconnect at some point
        yield message


    Limitations:
        - You cannot yield True.
    """
    yield_queue = Queue.Queue()

    def do_yield(msg):
        yield_queue.put(msg)
        yield_queue.get()

    def wrapper(self, *args, **kwargs):
        self.yield_from_callback = do_yield

        def run():
            try:
                fun(self, *args, **kwargs)
                yield_queue.put(True)
            except Exception as e:
                yield_queue.put(e)

        threading.Thread(target=run, name="YieldFromCallbackThread").start()
        while True:
            msg = yield_queue.get()
            if msg is True:
                break
            elif isinstance(msg, Exception):
                # TODO: Include func name?
                raise ProtocolException("Error in %s: %s" % (fun.__name__, repr(msg)), msg)
            else:
                yield msg
                yield_queue.put(None)

        self.yield_from_callback = None

    return wrapper