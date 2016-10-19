import socket

from OpenSSL import SSL

import mitmproxy.net.tcp
from mitmproxy import tcp
from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.proxy.protocol import base


class RawTCPLayer(base.Layer):
    chunk_size = 4096

    def __init__(self, ctx, ignore=False):
        self.ignore = ignore
        super().__init__(ctx)

    def __call__(self):
        self.connect()

        if not self.ignore:
            f = tcp.TCPFlow(self.client_conn, self.server_conn, self)
            self.channel.ask("tcp_start", f)

        buf = memoryview(bytearray(self.chunk_size))

        client = self.client_conn.connection
        server = self.server_conn.connection
        conns = [client, server]

        try:
            while not self.channel.should_exit.is_set():
                r = mitmproxy.net.tcp.ssl_read_select(conns, 10)
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

                    tcp_message = tcp.TCPMessage(dst == server, buf[:size].tobytes())
                    if not self.ignore:
                        f.messages.append(tcp_message)
                        self.channel.ask("tcp_message", f)
                    dst.sendall(tcp_message.content)

        except (socket.error, exceptions.TcpException, SSL.Error) as e:
            if not self.ignore:
                f.error = flow.Error("TCP connection closed unexpectedly: {}".format(repr(e)))
                self.channel.tell("tcp_error", f)
        finally:
            if not self.ignore:
                self.channel.tell("tcp_end", f)
