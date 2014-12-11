from __future__ import absolute_import
import select
import socket
from .primitives import ProtocolHandler
from netlib.utils import cleanBin


class TCPHandler(ProtocolHandler):
    """
    TCPHandler acts as a generic TCP forwarder.
    Data will be .log()ed, but not stored any further.
    """

    chunk_size = 4096

    def __init__(self, c, log=True):
        super(TCPHandler, self).__init__(c)
        self.log = log

    def handle_messages(self):
        self.c.establish_server_connection()

        server = "%s:%s" % self.c.server_conn.address()[:2]
        buf = memoryview(bytearray(self.chunk_size))
        conns = [self.c.client_conn.rfile, self.c.server_conn.rfile]

        try:
            while True:
                r, _, _ = select.select(conns, [], [], 10)
                for rfile in r:
                    if self.c.client_conn.rfile == rfile:
                        src, dst = self.c.client_conn, self.c.server_conn
                        direction = "-> tcp ->"
                        src_str, dst_str = "client", server
                    else:
                        dst, src = self.c.client_conn, self.c.server_conn
                        direction = "<- tcp <-"
                        dst_str, src_str = "client", server

                    closed = False
                    if src.ssl_established:
                        # Unfortunately, pyOpenSSL lacks a recv_into function.
                        # We need to read a single byte before .pending()
                        # becomes usable
                        contents = src.rfile.read(1)
                        contents += src.rfile.read(src.connection.pending())
                        if not contents:
                            closed = True
                    else:
                        size = src.connection.recv_into(buf)
                        if not size:
                            closed = True

                    if closed:
                        conns.remove(src.rfile)
                        # Shutdown connection to the other peer
                        if dst.ssl_established:
                            dst.connection.shutdown()
                        else:
                            dst.connection.shutdown(socket.SHUT_WR)

                        if len(conns) == 0:
                            return
                        continue

                    if src.ssl_established or dst.ssl_established:
                        # if one of the peers is over SSL, we need to send
                        # bytes/strings
                        if not src.ssl_established:
                            # we revc'd into buf but need bytes/string now.
                            contents = buf[:size].tobytes()
                        if self.log:
                            self.c.log(
                                "%s %s\r\n%s" % (
                                    direction, dst_str, cleanBin(contents)
                                ),
                                "info"
                            )
                        dst.connection.send(contents)
                    else:
                        # socket.socket.send supports raw bytearrays/memoryviews
                        if self.log:
                            self.c.log(
                                "%s %s\r\n%s" % (
                                    direction, dst_str, cleanBin(buf.tobytes())
                                ),
                                "info"
                            )
                        dst.connection.send(buf[:size])
        except socket.error as e:
            self.c.log("TCP connection closed unexpectedly.", "debug")
            return
