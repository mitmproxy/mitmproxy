from . import ProtocolHandler
import select, socket
from cStringIO import StringIO


class TCPHandler(ProtocolHandler):
    """
    TCPHandler acts as a generic TCP forwarder.
    Data will be .log()ed, but not stored any further.
    """
    def handle_messages(self):
        self.c.establish_server_connection()
        conns = [self.c.client_conn.rfile, self.c.server_conn.rfile]
        while not self.c.close:
            r, _, _ = select.select(conns, [], [], 10)
            for rfile in r:
                if self.c.client_conn.rfile == rfile:
                    src, dst = self.c.client_conn, self.c.server_conn
                    direction = "-> tcp ->"
                    dst_str = "%s:%s" % self.c.server_conn.address()[:2]
                else:
                    dst, src = self.c.client_conn, self.c.server_conn
                    direction = "<- tcp <-"
                    dst_str = "client"

                data = StringIO()
                while range(4096):
                    # Do non-blocking select() to see if there is further data on in the buffer.
                    r, _, _ = select.select([rfile], [], [], 0)
                    if len(r):
                        d = rfile.read(1)
                        if d == "":  # connection closed
                            break
                        data.write(d)
                        # OpenSSL Connections have an internal buffer that might
                        # contain data altough everything is read from the socket.
                        # Thankfully, connection.pending() returns the amount of
                        # bytes in this buffer, so we can read it completely at
                        # once.
                        if src.ssl_established:
                            data.write(rfile.read(src.connection.pending()))
                    else:  # no data left, but not closed yet
                        break
                data = data.getvalue()

                if data == "":  # no data received, rfile is closed
                    self.c.log("Close writing connection to %s" % dst_str)
                    conns.remove(rfile)
                    if dst.ssl_established:
                        dst.connection.shutdown()
                    else:
                        dst.connection.shutdown(socket.SHUT_WR)
                    if len(conns) == 0:
                        self.c.close = True
                    break

                self.c.log("%s %s\r\n%s" % (direction, dst_str,data))
                dst.wfile.write(data)
                dst.wfile.flush()
