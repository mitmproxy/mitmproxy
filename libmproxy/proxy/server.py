from __future__ import absolute_import, print_function

import traceback
import sys
import socket
from netlib import tcp
from netlib.http.http1 import HTTP1Protocol
from netlib.tcp import NetLibError

from .. import protocol2
from .. import proxy_modes
from ..exceptions import ProtocolException, ServerException
from .primitives import Log, Kill
from .connection import ClientConnection


class DummyServer:
    bound = False

    def __init__(self, config):
        self.config = config

    def start_slave(self, *args):
        pass

    def shutdown(self):
        pass


class ProxyServer(tcp.TCPServer):
    allow_reuse_address = True
    bound = True

    def __init__(self, config):
        """
            Raises ProxyServerError if there's a startup problem.
        """
        self.config = config
        try:
            super(ProxyServer, self).__init__((config.host, config.port))
        except socket.error as e:
            raise ServerException('Error starting proxy server: ' + repr(e), e)
        self.channel = None

    def start_slave(self, klass, channel):
        slave = klass(channel, self)
        slave.start()

    def set_channel(self, channel):
        self.channel = channel

    def handle_client_connection(self, conn, client_address):
        h = ConnectionHandler(
            conn,
            client_address,
            self.config,
            self.channel
        )
        h.handle()


class ConnectionHandler(object):
    def __init__(self, client_conn, client_address, config, channel):
        self.config = config
        """@type: libmproxy.proxy.config.ProxyConfig"""
        self.client_conn = ClientConnection(
            client_conn,
            client_address,
            None)
        """@type: libmproxy.proxy.connection.ClientConnection"""
        self.channel = channel
        """@type: libmproxy.controller.Channel"""

    def _create_root_layer(self):
        root_context = protocol2.RootContext(
            self.client_conn,
            self.config,
            self.channel
        )

        mode = self.config.mode
        if mode == "upstream":
            return proxy_modes.HttpUpstreamProxy(
                root_context,
                self.config.upstream_server.address
            )
        elif mode == "transparent":
            return proxy_modes.TransparentProxy(root_context)
        elif mode == "reverse":
            server_tls = self.config.upstream_server.scheme == "https"
            return proxy_modes.ReverseProxy(
                root_context,
                self.config.upstream_server.address,
                server_tls
            )
        elif mode == "socks5":
            return proxy_modes.Socks5Proxy(root_context)
        elif mode == "regular":
            return proxy_modes.HttpProxy(root_context)
        elif callable(mode):  # pragma: nocover
            return mode(root_context)
        else:  # pragma: nocover
            raise ValueError("Unknown proxy mode: %s" % mode)

    def handle(self):
        self.log("clientconnect", "info")

        root_layer = self._create_root_layer()

        try:
            root_layer()
        except Kill:
            self.log("Connection killed", "info")
        except ProtocolException as e:
            self.log(e, "info")
            # If an error propagates to the topmost level,
            # we send an HTTP error response, which is both
            # understandable by HTTP clients and humans.
            try:
                error_response = protocol2.make_error_response(502, repr(e))
                self.client_conn.send(HTTP1Protocol().assemble(error_response))
            except NetLibError:
                pass
        except Exception:
            self.log(traceback.format_exc(), "error")
            print(traceback.format_exc(), file=sys.stderr)
            print("mitmproxy has crashed!", file=sys.stderr)
            print("Please lodge a bug report at: https://github.com/mitmproxy/mitmproxy", file=sys.stderr)

        self.log("clientdisconnect", "info")
        self.client_conn.finish()

    def log(self, msg, level):
        msg = "{}: {}".format(repr(self.client_conn.address), msg)
        self.channel.tell("log", Log(msg, level))
