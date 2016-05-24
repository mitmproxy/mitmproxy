from __future__ import (absolute_import, print_function, division)
import socket
import six
import sys

from OpenSSL import SSL
from netlib.exceptions import TcpException

from netlib.tcp import ssl_read_select
from netlib.utils import clean_bin
from ..exceptions import ProtocolException
from ..models import Error
from ..models.tcp import TCPFlow, TCPMessage

from .base import Layer


class RawTCPLayer(Layer):
    chunk_size = 4096

    def __init__(self, ctx, ignore=False):
        self.ignore = ignore
        super(RawTCPLayer, self).__init__(ctx)

    def __call__(self):
        self.connect()

        if not self.ignore:
            flow = TCPFlow(self.client_conn, self.server_conn, self)
            self.channel.ask("tcp_open", flow)

        buf = memoryview(bytearray(self.chunk_size))

        client = self.client_conn.connection
        server = self.server_conn.connection
        conns = [client, server]

        try:
            while not self.channel.should_exit.is_set():
                r = ssl_read_select(conns, 10)
                for conn in r:
                    dst = server if conn == client else client

                    size = conn.recv_into(buf, self.chunk_size)
                    if not size:
                        conns.remove(conn)
                        # Shutdown connection to the other peer
                        if isinstance(conn, SSL.Connection):
                            # We can't half-close a connection, so we just close everything here.
                            # Sockets will be cleaned up on a higher level.
                            return
                        else:
                            dst.shutdown(socket.SHUT_WR)

                        if len(conns) == 0:
                            return
                        continue

                    tcp_message = TCPMessage(dst == server, buf[:size].tobytes())
                    if not self.ignore:
                        flow.messages.append(tcp_message)
                        self.channel.ask("tcp_message", flow)
                    dst.sendall(tcp_message.content)

        except (socket.error, TcpException, SSL.Error) as e:
            if not self.ignore:
                flow.error = Error("TCP connection closed unexpectedly: {}".format(repr(e)))
                self.channel.tell("tcp_error", flow)
        finally:
            if not self.ignore:
                self.channel.tell("tcp_close", flow)
