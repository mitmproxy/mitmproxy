from __future__ import (absolute_import, print_function, division)

import traceback
import sys
import socket
import six

from netlib import tcp
from netlib.exceptions import TcpException
from netlib.http.http1 import assemble_response
from ..exceptions import ProtocolException, ServerException, ClientHandshakeException
from ..protocol import Kill
from ..models import ClientConnection, make_error_response
from .modes import HttpUpstreamProxy, HttpProxy, ReverseProxy, TransparentProxy, Socks5Proxy
from .root_context import RootContext, Log


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
            six.reraise(
                ServerException,
                ServerException('Error starting proxy server: ' + repr(e)),
                sys.exc_info()[2]
            )
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
        """@type: mitmproxy.proxy.config.ProxyConfig"""
        self.client_conn = ClientConnection(
            client_conn,
            client_address,
            None)
        """@type: mitmproxy.proxy.connection.ClientConnection"""
        self.channel = channel
        """@type: mitmproxy.controller.Channel"""

    def _create_root_layer(self):
        root_context = RootContext(
            self.client_conn,
            self.config,
            self.channel
        )

        mode = self.config.mode
        if mode == "upstream":
            return HttpUpstreamProxy(
                root_context,
                self.config.upstream_server.address
            )
        elif mode == "transparent":
            return TransparentProxy(root_context)
        elif mode == "reverse":
            server_tls = self.config.upstream_server.scheme == "https"
            return ReverseProxy(
                root_context,
                self.config.upstream_server.address,
                server_tls
            )
        elif mode == "socks5":
            return Socks5Proxy(root_context)
        elif mode == "regular":
            return HttpProxy(root_context)
        elif callable(mode):  # pragma: no cover
            return mode(root_context)
        else:  # pragma: no cover
            raise ValueError("Unknown proxy mode: %s" % mode)

    def handle(self):
        self.log("clientconnect", "info")

        root_layer = self._create_root_layer()
        root_layer = self.channel.ask("clientconnect", root_layer)
        if root_layer == Kill:
            def root_layer():
                raise Kill()

        try:
            root_layer()
        except Kill:
            self.log("Connection killed", "info")
        except ProtocolException as e:

            if isinstance(e, ClientHandshakeException):
                self.log(
                    "Client Handshake failed. "
                    "The client may not trust the proxy's certificate for {}.".format(e.server),
                    "error"
                )
                self.log(repr(e), "debug")
            else:
                self.log(repr(e), "info")

                self.log(traceback.format_exc(), "debug")
            # If an error propagates to the topmost level,
            # we send an HTTP error response, which is both
            # understandable by HTTP clients and humans.
            try:
                error_response = make_error_response(502, repr(e))
                self.client_conn.send(assemble_response(error_response))
            except TcpException:
                pass
        except Exception:
            self.log(traceback.format_exc(), "error")
            print(traceback.format_exc(), file=sys.stderr)
            print("mitmproxy has crashed!", file=sys.stderr)
            print("Please lodge a bug report at: https://github.com/mitmproxy/mitmproxy", file=sys.stderr)

        self.log("clientdisconnect", "info")
        self.channel.tell("clientdisconnect", root_layer)
        self.client_conn.finish()

    def log(self, msg, level):
        msg = "{}: {}".format(repr(self.client_conn.address), msg)
        self.channel.tell("log", Log(msg, level))
