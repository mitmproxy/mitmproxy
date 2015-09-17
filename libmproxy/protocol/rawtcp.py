from __future__ import (absolute_import, print_function, division)
import socket
import select
import six
import sys

from OpenSSL import SSL
from netlib.exceptions import TcpException

from netlib.tcp import ssl_read_select
from netlib.utils import clean_bin
from ..exceptions import ProtocolException
from .base import Layer


class RawTCPLayer(Layer):
    chunk_size = 4096

    def __init__(self, ctx, logging=True):
        self.logging = logging
        super(RawTCPLayer, self).__init__(ctx)

    def __call__(self):
        self.connect()

        buf = memoryview(bytearray(self.chunk_size))

        client = self.client_conn.connection
        server = self.server_conn.connection
        conns = [client, server]

        try:
            while True:
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

                    dst.sendall(buf[:size])

                    if self.logging:
                        # log messages are prepended with the client address,
                        # hence the "weird" direction string.
                        if dst == server:
                            direction = "-> tcp -> {}".format(repr(self.server_conn.address))
                        else:
                            direction = "<- tcp <- {}".format(repr(self.server_conn.address))
                        data = clean_bin(buf[:size].tobytes())
                        self.log(
                            "{}\r\n{}".format(direction, data),
                            "info"
                        )

        except (socket.error, TcpException, SSL.Error) as e:
            six.reraise(
                ProtocolException,
                ProtocolException("TCP connection closed unexpectedly: {}".format(repr(e))),
                sys.exc_info()[2]
            )
