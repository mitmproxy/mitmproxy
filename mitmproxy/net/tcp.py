import os
import errno
import select
import socket
import sys
import threading
import time
import traceback

from typing import Optional  # noqa

from mitmproxy.net import tls

from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy import exceptions
from mitmproxy.coretypes import basethread

socket_fileobject = socket.SocketIO

# workaround for https://bugs.python.org/issue29515
# Python 3.6 for Windows is missing a constant
IPPROTO_IPV6 = getattr(socket, "IPPROTO_IPV6", 41)


class _FileLike:
    BLOCKSIZE = 1024 * 32

    def __init__(self, o):
        self.o = o
        self._log = None
        self.first_byte_timestamp = None

    def set_descriptor(self, o):
        self.o = o

    def __getattr__(self, attr):
        return getattr(self.o, attr)

    def start_log(self):
        """
            Starts or resets the log.

            This will store all bytes read or written.
        """
        self._log = []

    def stop_log(self):
        """
            Stops the log.
        """
        self._log = None

    def is_logging(self):
        return self._log is not None

    def get_log(self):
        """
            Returns the log as a string.
        """
        if not self.is_logging():
            raise ValueError("Not logging!")
        return b"".join(self._log)

    def add_log(self, v):
        if self.is_logging():
            self._log.append(v)

    def reset_timestamps(self):
        self.first_byte_timestamp = None


class Writer(_FileLike):

    def flush(self):
        """
            May raise exceptions.TcpDisconnect
        """
        if hasattr(self.o, "flush"):
            try:
                self.o.flush()
            except (socket.error, IOError) as v:
                raise exceptions.TcpDisconnect(str(v))

    def write(self, v):
        """
            May raise exceptions.TcpDisconnect
        """
        if v:
            self.first_byte_timestamp = self.first_byte_timestamp or time.time()
            try:
                if hasattr(self.o, "sendall"):
                    self.add_log(v)
                    return self.o.sendall(v)
                else:
                    r = self.o.write(v)
                    self.add_log(v[:r])
                    return r
            except (SSL.Error, socket.error) as e:
                raise exceptions.TcpDisconnect(str(e))


class Reader(_FileLike):

    def read(self, length):
        """
            If length is -1, we read until connection closes.
        """
        result = b''
        start = time.time()
        while length == -1 or length > 0:
            if length == -1 or length > self.BLOCKSIZE:
                rlen = self.BLOCKSIZE
            else:
                rlen = length
            try:
                data = self.o.read(rlen)
            except SSL.ZeroReturnError:
                # TLS connection was shut down cleanly
                break
            except (SSL.WantWriteError, SSL.WantReadError):
                # From the OpenSSL docs:
                # If the underlying BIO is non-blocking, SSL_read() will also return when the
                # underlying BIO could not satisfy the needs of SSL_read() to continue the
                # operation. In this case a call to SSL_get_error with the return value of
                # SSL_read() will yield SSL_ERROR_WANT_READ or SSL_ERROR_WANT_WRITE.
                # 300 is OpenSSL default timeout
                timeout = self.o.gettimeout() or 300
                if (time.time() - start) < timeout:
                    time.sleep(0.1)
                    continue
                else:
                    raise exceptions.TcpTimeout()
            except socket.timeout:
                raise exceptions.TcpTimeout()
            except socket.error as e:
                raise exceptions.TcpDisconnect(str(e))
            except SSL.SysCallError as e:
                if e.args == (-1, 'Unexpected EOF'):
                    break
                raise exceptions.TlsException(str(e))
            except SSL.Error as e:
                raise exceptions.TlsException(str(e))
            self.first_byte_timestamp = self.first_byte_timestamp or time.time()
            if not data:
                break
            result += data
            if length != -1:
                length -= len(data)
        self.add_log(result)
        return result

    def readline(self, size=None):
        result = b''
        bytes_read = 0
        while True:
            if size is not None and bytes_read >= size:
                break
            ch = self.read(1)
            bytes_read += 1
            if not ch:
                break
            else:
                result += ch
                if ch == b'\n':
                    break
        return result

    def safe_read(self, length):
        """
            Like .read, but is guaranteed to either return length bytes, or
            raise an exception.
        """
        result = self.read(length)
        if length != -1 and len(result) != length:
            if not result:
                raise exceptions.TcpDisconnect()
            else:
                raise exceptions.TcpReadIncomplete(
                    "Expected %s bytes, got %s" % (length, len(result))
                )
        return result

    def peek(self, length):
        """
        Tries to peek into the underlying file object.

        Returns:
            Up to the next N bytes if peeking is successful.

        Raises:
            exceptions.TcpException if there was an error with the socket
            TlsException if there was an error with pyOpenSSL.
            NotImplementedError if the underlying file object is not a [pyOpenSSL] socket
        """
        if isinstance(self.o, socket_fileobject):
            try:
                return self.o._sock.recv(length, socket.MSG_PEEK)
            except socket.error as e:
                raise exceptions.TcpException(repr(e))
        elif isinstance(self.o, SSL.Connection):
            try:
                return self.o.recv(length, socket.MSG_PEEK)
            except SSL.Error as e:
                raise exceptions.TlsException(str(e))
        else:
            raise NotImplementedError("Can only peek into (pyOpenSSL) sockets")


def ssl_read_select(rlist, timeout):
    """
    This is a wrapper around select.select() which also works for SSL.Connections
    by taking ssl_connection.pending() into account.

    Caveats:
        If .pending() > 0 for any of the connections in rlist, we avoid the select syscall
        and **will not include any other connections which may or may not be ready**.

    Args:
        rlist: wait until ready for reading

    Returns:
        subset of rlist which is ready for reading.
    """
    return [
        conn for conn in rlist
        if isinstance(conn, SSL.Connection) and conn.pending() > 0
    ] or select.select(rlist, (), (), timeout)[0]


def close_socket(sock):
    """
    Does a hard close of a socket, without emitting a RST.
    """
    try:
        # We already indicate that we close our end.
        # may raise "Transport endpoint is not connected" on Linux
        sock.shutdown(socket.SHUT_WR)

        # Section 4.2.2.13 of RFC 1122 tells us that a close() with any pending
        # readable data could lead to an immediate RST being sent (which is the
        # case on Windows).
        # http://ia600609.us.archive.org/22/items/TheUltimateSo_lingerPageOrWhyIsMyTcpNotReliable/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable.html
        #
        # This in turn results in the following issue: If we send an error page
        # to the client and then close the socket, the RST may be received by
        # the client before the error page and the users sees a connection
        # error rather than the error page. Thus, we try to empty the read
        # buffer on Windows first. (see
        # https://github.com/mitmproxy/mitmproxy/issues/527#issuecomment-93782988)
        #

        if os.name == "nt":  # pragma: no cover
            # We cannot rely on the shutdown()-followed-by-read()-eof technique
            # proposed by the page above: Some remote machines just don't send
            # a TCP FIN, which would leave us in the unfortunate situation that
            # recv() would block infinitely. As a workaround, we set a timeout
            # here even if we are in blocking mode.
            sock.settimeout(sock.gettimeout() or 20)

            # limit at a megabyte so that we don't read infinitely
            for _ in range(1024 ** 3 // 4096):
                # may raise a timeout/disconnect exception.
                if not sock.recv(4096):
                    break

        # Now we can close the other half as well.
        sock.shutdown(socket.SHUT_RD)

    except socket.error:
        pass

    sock.close()


class _Connection:

    rbufsize = -1
    wbufsize = -1

    def _makefile(self):
        """
        Set up .rfile and .wfile attributes from .connection
        """
        # Ideally, we would use the Buffered IO in Python 3 by default.
        # Unfortunately, the implementation of .peek() is broken for n>1 bytes,
        # as it may just return what's left in the buffer and not all the bytes we want.
        # As a workaround, we just use unbuffered sockets directly.
        # https://mail.python.org/pipermail/python-dev/2009-June/089986.html
        self.rfile = Reader(socket.SocketIO(self.connection, "rb"))
        self.wfile = Writer(socket.SocketIO(self.connection, "wb"))

    def __init__(self, connection):
        if connection:
            self.connection = connection
            self.ip_address = connection.getpeername()
            self._makefile()
        else:
            self.connection = None
            self.ip_address = None
            self.rfile = None
            self.wfile = None

        self.tls_established = False
        self.finished = False

    def get_current_cipher(self):
        if not self.tls_established:
            return None

        name = self.connection.get_cipher_name()
        bits = self.connection.get_cipher_bits()
        version = self.connection.get_cipher_version()
        return name, bits, version

    def finish(self):
        self.finished = True
        # If we have an SSL connection, wfile.close == connection.close
        # (We call _FileLike.set_descriptor(conn))
        # Closing the socket is not our task, therefore we don't call close
        # then.
        if not isinstance(self.connection, SSL.Connection):
            if not getattr(self.wfile, "closed", False):
                try:
                    self.wfile.flush()
                    self.wfile.close()
                except exceptions.TcpDisconnect:
                    pass

            self.rfile.close()
        else:
            try:
                self.connection.shutdown()
            except SSL.Error:
                pass


class ConnectionCloser:
    def __init__(self, conn):
        self.conn = conn
        self._canceled = False

    def pop(self):
        """
            Cancel the current closer, and return a fresh one.
        """
        self._canceled = True
        return ConnectionCloser(self.conn)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self._canceled:
            self.conn.close()


class TCPClient(_Connection):

    def __init__(self, address, source_address=None, spoof_source_address=None):
        super().__init__(None)
        self.address = address
        self.source_address = source_address
        self.cert = None
        self.server_certs = []
        self.sni = None
        self.spoof_source_address = spoof_source_address

    @property
    def ssl_verification_error(self) -> Optional[exceptions.InvalidCertificateException]:
        return getattr(self.connection, "cert_error", None)

    def close(self):
        # Make sure to close the real socket, not the SSL proxy.
        # OpenSSL is really good at screwing up, i.e. when trying to recv from a failed connection,
        # it tries to renegotiate...
        if self.connection:
            if isinstance(self.connection, SSL.Connection):
                close_socket(self.connection._socket)
            else:
                close_socket(self.connection)

    def convert_to_tls(self, sni=None, alpn_protos=None, **sslctx_kwargs):
        context = tls.create_client_context(
            alpn_protos=alpn_protos,
            sni=sni,
            **sslctx_kwargs
        )
        self.connection = SSL.Connection(context, self.connection)
        if sni:
            self.sni = sni
            self.connection.set_tlsext_host_name(sni.encode("idna"))
        self.connection.set_connect_state()
        try:
            self.connection.do_handshake()
        except SSL.Error as v:
            if self.ssl_verification_error:
                raise self.ssl_verification_error
            else:
                raise exceptions.TlsException("SSL handshake error: %s" % repr(v))

        self.cert = certs.Cert(self.connection.get_peer_certificate())

        # Keep all server certificates in a list
        for i in self.connection.get_peer_cert_chain():
            self.server_certs.append(certs.Cert(i))

        self.tls_established = True
        self.rfile.set_descriptor(self.connection)
        self.wfile.set_descriptor(self.connection)

    def makesocket(self, family, type, proto):
        # some parties (cuckoo sandbox) need to hook this
        return socket.socket(family, type, proto)

    def create_connection(self, timeout=None):
        # Based on the official socket.create_connection implementation of Python 3.6.
        # https://github.com/python/cpython/blob/3cc5817cfaf5663645f4ee447eaed603d2ad290a/Lib/socket.py

        err = None
        for res in socket.getaddrinfo(self.address[0], self.address[1], 0, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            sock = None
            try:
                sock = self.makesocket(af, socktype, proto)
                if timeout:
                    sock.settimeout(timeout)
                if self.source_address:
                    sock.bind(self.source_address)
                if self.spoof_source_address:
                    try:
                        if not sock.getsockopt(socket.SOL_IP, socket.IP_TRANSPARENT):
                            sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)  # pragma: windows no cover  pragma: osx no cover
                    except Exception as e:
                        # socket.IP_TRANSPARENT might not be available on every OS and Python version
                        if sock is not None:
                            sock.close()
                        raise exceptions.TcpException(
                            "Failed to spoof the source address: " + str(e)
                        )
                sock.connect(sa)
                return sock

            except socket.error as _:
                err = _
                if sock is not None:
                    sock.close()

        if err is not None:
            raise err
        else:
            raise socket.error("getaddrinfo returns an empty list")  # pragma: no cover

    def connect(self):
        try:
            connection = self.create_connection()
        except (socket.error, IOError) as err:
            raise exceptions.TcpException(
                'Error connecting to "%s": %s' %
                (self.address[0], err)
            )
        self.connection = connection
        self.source_address = connection.getsockname()
        self.ip_address = connection.getpeername()
        self._makefile()
        return ConnectionCloser(self)

    def settimeout(self, n):
        self.connection.settimeout(n)

    def gettimeout(self):
        return self.connection.gettimeout()

    def get_alpn_proto_negotiated(self):
        if self.tls_established:
            return self.connection.get_alpn_proto_negotiated()
        else:
            return b""


class BaseHandler(_Connection):

    """
        The instantiator is expected to call the handle() and finish() methods.
    """

    def __init__(self, connection, address, server):
        super().__init__(connection)
        self.address = address
        self.server = server
        self.clientcert = None

    def convert_to_tls(self, cert, key, **sslctx_kwargs):
        """
        Convert connection to SSL.
        For a list of parameters, see tls.create_server_context(...)
        """

        context = tls.create_server_context(
            cert=cert,
            key=key,
            **sslctx_kwargs)
        self.connection = SSL.Connection(context, self.connection)
        self.connection.set_accept_state()
        try:
            self.connection.do_handshake()
        except SSL.Error as v:
            raise exceptions.TlsException("SSL handshake error: %s" % repr(v))
        self.tls_established = True
        cert = self.connection.get_peer_certificate()
        if cert:
            self.clientcert = certs.Cert(cert)
        self.rfile.set_descriptor(self.connection)
        self.wfile.set_descriptor(self.connection)

    def handle(self):  # pragma: no cover
        raise NotImplementedError

    def settimeout(self, n):
        self.connection.settimeout(n)

    def get_alpn_proto_negotiated(self):
        if self.tls_established:
            return self.connection.get_alpn_proto_negotiated()
        else:
            return b""


class Counter:
    def __init__(self):
        self._count = 0
        self._lock = threading.Lock()

    @property
    def count(self):
        with self._lock:
            return self._count

    def __enter__(self):
        with self._lock:
            self._count += 1

    def __exit__(self, *args):
        with self._lock:
            self._count -= 1


class TCPServer:

    def __init__(self, address):
        self.address = address
        self.__is_shut_down = threading.Event()
        self.__is_shut_down.set()
        self.__shutdown_request = False

        if self.address[0] == 'localhost':
            raise socket.error("Binding to 'localhost' is prohibited. Please use '::1' or '127.0.0.1' directly.")

        self.socket = None

        try:
            # First try to bind an IPv6 socket, attempting to enable IPv4 support if the OS supports it.
            # This allows us to accept connections for ::1 and 127.0.0.1 on the same socket.
            # Only works if self.address == ""
            self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.setsockopt(IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            self.socket.bind(self.address)
        except socket.error:
            if self.socket:
                self.socket.close()
            self.socket = None

        if not self.socket:
            try:
                # Binding to an IPv6 + IPv4 socket failed, lets fall back to IPv4 only.
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                self.socket.bind(self.address)
            except socket.error:
                if self.socket:
                    self.socket.close()
                self.socket = None

        if not self.socket:
            # Binding to an IPv4 only socket failed, lets fall back to IPv6 only.
            self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.bind(self.address)

        self.address = self.socket.getsockname()
        self.socket.listen()
        self.handler_counter = Counter()

    def connection_thread(self, connection, client_address):
        with self.handler_counter:
            try:
                self.handle_client_connection(connection, client_address)
            except OSError as e:  # pragma: no cover
                # This catches situations where the underlying connection is
                # closed beneath us. Syscalls on the connection object at this
                # point returns EINVAL. If this happens, we close the socket and
                # move on.
                if not e.errno == errno.EINVAL:
                    raise
            except:
                self.handle_error(connection, client_address)
            finally:
                close_socket(connection)

    def serve_forever(self, poll_interval=0.1):
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                r, w_, e_ = select.select([self.socket], [], [], poll_interval)
                if self.socket in r:
                    connection, client_address = self.socket.accept()
                    t = basethread.BaseThread(
                        "TCPConnectionHandler (%s: %s:%s -> %s:%s)" % (
                            self.__class__.__name__,
                            client_address[0],
                            client_address[1],
                            self.address[0],
                            self.address[1],
                        ),
                        target=self.connection_thread,
                        args=(connection, client_address),
                    )
                    t.setDaemon(1)
                    try:
                        t.start()
                    except threading.ThreadError:
                        self.handle_error(connection, client_address)
                        connection.close()
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        self.__shutdown_request = True
        self.__is_shut_down.wait()
        self.socket.close()
        self.handle_shutdown()

    def handle_error(self, connection_, client_address, fp=sys.stderr):
        """
            Called when handle_client_connection raises an exception.
        """
        # If a thread has persisted after interpreter exit, the module might be
        # none.
        if traceback:
            exc = str(traceback.format_exc())
            print(u'-' * 40, file=fp)
            print(
                u"Error in processing of request from %s" % repr(client_address), file=fp)
            print(exc, file=fp)
            print(u'-' * 40, file=fp)

    def handle_client_connection(self, conn, client_address):  # pragma: no cover
        """
            Called after client connection.
        """
        raise NotImplementedError

    def handle_shutdown(self):
        """
            Called after server shutdown.
        """

    def wait_for_silence(self, timeout=5):
        start = time.time()
        while 1:
            if time.time() - start >= timeout:
                raise exceptions.Timeout(
                    "%s service threads still alive" %
                    self.handler_counter.count
                )
            if self.handler_counter.count == 0:
                return
