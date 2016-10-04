from __future__ import absolute_import, print_function, division

import socket
import sys
import traceback

import six

import netlib.exceptions
from mitmproxy import exceptions
from mitmproxy import models
from mitmproxy import controller
from mitmproxy.proxy import modes
from mitmproxy.proxy import root_context
from netlib import tcp
from netlib.http import http1


class DummyServer:
    bound = False

    def __init__(self, config):
        self.config = config

    def set_channel(self, channel):
        pass

    def serve_forever(self):
        pass

    def shutdown(self):
        pass


class ProxyServer(tcp.TCPServer):
    allow_reuse_address = True
    bound = True

    def __init__(self, config):
        """
            Raises ServerException if there's a startup problem.
        """
        self.config = config
        try:
            super(ProxyServer, self).__init__(
                (config.options.listen_host, config.options.listen_port)
            )
        except socket.error as e:
            six.reraise(
                exceptions.ServerException,
                exceptions.ServerException('Error starting proxy server: ' + repr(e)),
                sys.exc_info()[2]
            )
        self.channel = None

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
        self.client_conn = models.ClientConnection(
            client_conn,
            client_address,
            None)
        """@type: mitmproxy.proxy.connection.ClientConnection"""
        self.channel = channel
        """@type: mitmproxy.controller.Channel"""

    def _create_root_layer(self):
        root_ctx = root_context.RootContext(
            self.client_conn,
            self.config,
            self.channel
        )

        mode = self.config.options.mode
        if mode == "upstream":
            return modes.HttpUpstreamProxy(
                root_ctx,
                self.config.upstream_server.address
            )
        elif mode == "transparent":
            return modes.TransparentProxy(root_ctx)
        elif mode == "reverse":
            server_tls = self.config.upstream_server.scheme == "https"
            return modes.ReverseProxy(
                root_ctx,
                self.config.upstream_server.address,
                server_tls
            )
        elif mode == "socks5":
            return modes.Socks5Proxy(root_ctx)
        elif mode == "regular":
            return modes.HttpProxy(root_ctx)
        elif callable(mode):  # pragma: no cover
            return mode(root_ctx)
        else:  # pragma: no cover
            raise ValueError("Unknown proxy mode: %s" % mode)

    def handle(self):
        self.log("clientconnect", "info")

        root_layer = self._create_root_layer()

        try:
            root_layer = self.channel.ask("clientconnect", root_layer)
            root_layer()
        except exceptions.Kill:
            self.log("Connection killed", "info")
        except exceptions.ProtocolException as e:

            if isinstance(e, exceptions.ClientHandshakeException):
                self.log(
                    "Client Handshake failed. "
                    "The client may not trust the proxy's certificate for {}.".format(e.server),
                    "warn"
                )
                self.log(repr(e), "debug")
            elif isinstance(e, exceptions.InvalidServerCertificate):
                self.log(str(e), "warn")
                self.log("Invalid certificate, closing connection. Pass --insecure to disable validation.", "warn")
            else:
                self.log(str(e), "warn")

                self.log(traceback.format_exc(), "debug")
            # If an error propagates to the topmost level,
            # we send an HTTP error response, which is both
            # understandable by HTTP clients and humans.
            try:
                error_response = models.make_error_response(502, repr(e))
                self.client_conn.send(http1.assemble_response(error_response))
            except netlib.exceptions.TcpException:
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
        self.channel.tell("log", controller.LogEntry(msg, level))
