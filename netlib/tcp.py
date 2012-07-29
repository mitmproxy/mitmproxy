import select, socket, threading, traceback, sys, time
from OpenSSL import SSL
import certutils

SSLv2_METHOD = SSL.SSLv2_METHOD
SSLv3_METHOD = SSL.SSLv3_METHOD
SSLv23_METHOD = SSL.SSLv23_METHOD
TLSv1_METHOD = SSL.TLSv1_METHOD

OP_ALL = SSL.OP_ALL
OP_CIPHER_SERVER_PREFERENCE = SSL.OP_CIPHER_SERVER_PREFERENCE
OP_COOKIE_EXCHANGE = SSL.OP_COOKIE_EXCHANGE
OP_DONT_INSERT_EMPTY_FRAGMENTS = SSL.OP_DONT_INSERT_EMPTY_FRAGMENTS
OP_EPHEMERAL_RSA = SSL.OP_EPHEMERAL_RSA
OP_MICROSOFT_BIG_SSLV3_BUFFER = SSL.OP_MICROSOFT_BIG_SSLV3_BUFFER
OP_MICROSOFT_SESS_ID_BUG = SSL.OP_MICROSOFT_SESS_ID_BUG
OP_MSIE_SSLV2_RSA_PADDING = SSL.OP_MSIE_SSLV2_RSA_PADDING
OP_NETSCAPE_CA_DN_BUG = SSL.OP_NETSCAPE_CA_DN_BUG
OP_NETSCAPE_CHALLENGE_BUG = SSL.OP_NETSCAPE_CHALLENGE_BUG
OP_NETSCAPE_DEMO_CIPHER_CHANGE_BUG = SSL.OP_NETSCAPE_DEMO_CIPHER_CHANGE_BUG
OP_NETSCAPE_REUSE_CIPHER_CHANGE_BUG = SSL.OP_NETSCAPE_REUSE_CIPHER_CHANGE_BUG
OP_NO_QUERY_MTU = SSL.OP_NO_QUERY_MTU
OP_NO_SSLv2 = SSL.OP_NO_SSLv2
OP_NO_SSLv3 = SSL.OP_NO_SSLv3
OP_NO_TICKET = SSL.OP_NO_TICKET
OP_NO_TLSv1 = SSL.OP_NO_TLSv1
OP_PKCS1_CHECK_1 = SSL.OP_PKCS1_CHECK_1
OP_PKCS1_CHECK_2 = SSL.OP_PKCS1_CHECK_2
OP_SINGLE_DH_USE = SSL.OP_SINGLE_DH_USE
OP_SSLEAY_080_CLIENT_DH_BUG = SSL.OP_SSLEAY_080_CLIENT_DH_BUG
OP_SSLREF2_REUSE_CERT_TYPE_BUG = SSL.OP_SSLREF2_REUSE_CERT_TYPE_BUG
OP_TLS_BLOCK_PADDING_BUG = SSL.OP_TLS_BLOCK_PADDING_BUG
OP_TLS_D5_BUG = SSL.OP_TLS_D5_BUG
OP_TLS_ROLLBACK_BUG = SSL.OP_TLS_ROLLBACK_BUG


class NetLibError(Exception): pass
class NetLibDisconnect(Exception): pass
class NetLibTimeout(Exception): pass


class FileLike:
    BLOCKSIZE = 1024 * 32
    def __init__(self, o):
        self.o = o

    def __getattr__(self, attr):
        return getattr(self.o, attr)

    def flush(self):
        try:
            if hasattr(self.o, "flush"):
                self.o.flush()
        except socket.error, v:
            raise NetLibDisconnect(str(v))

    def read(self, length):
        """
            If length is None, we read until connection closes.
        """
        result = ''
        start = time.time()
        while length == -1 or length > 0:
            try:
                data = self.o.read(self.BLOCKSIZE if length == -1 else length)
            except SSL.ZeroReturnError:
                break
            except SSL.WantReadError:
                if (time.time() - start) < self.o.gettimeout():
                    time.sleep(0.1)
                    continue
                else:
                    raise NetLibTimeout
            except socket.timeout:
                raise NetLibTimeout
            except socket.error:
                raise NetLibDisconnect
            except SSL.SysCallError, v:
                raise NetLibDisconnect
            if not data:
                break
            result += data
            if length != -1:
                length -= len(data)
        return result

    def write(self, v):
        if v:
            try:
                if hasattr(self.o, "sendall"):
                    return self.o.sendall(v)
                else:
                    r = self.o.write(v)
                    return r
            except (SSL.Error, socket.error):
                raise NetLibDisconnect()

    def readline(self, size = None):
        result = ''
        bytes_read = 0
        while True:
            if size is not None and bytes_read >= size:
                break
            try:
                ch = self.read(1)
            except NetLibDisconnect:
                break
            bytes_read += 1
            if not ch:
                break
            else:
                result += ch
                if ch == '\n':
                    break
        return result


class TCPClient:
    rbufsize = -1
    wbufsize = -1
    def __init__(self, host, port):
        self.host, self.port = host, port
        self.connection, self.rfile, self.wfile = None, None, None
        self.cert = None
        self.ssl_established = False

    def convert_to_ssl(self, clientcert=None, sni=None, method=TLSv1_METHOD, options=None):
        context = SSL.Context(method)
        if not options is None:
            ctx.set_options(options)
        if clientcert:
            context.use_certificate_file(self.clientcert)
        self.connection = SSL.Connection(context, self.connection)
        self.ssl_established = True
        if sni:
            self.connection.set_tlsext_host_name(sni)
        self.connection.set_connect_state()
        try:
            self.connection.do_handshake()
        except SSL.Error, v:
            raise NetLibError("SSL handshake error: %s"%str(v))
        self.cert = certutils.SSLCert(self.connection.get_peer_certificate())
        self.rfile = FileLike(self.connection)
        self.wfile = FileLike(self.connection)

    def connect(self):
        try:
            addr = socket.gethostbyname(self.host)
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            connection.connect((addr, self.port))
            self.rfile = FileLike(connection.makefile('rb', self.rbufsize))
            self.wfile = FileLike(connection.makefile('wb', self.wbufsize))
        except socket.error, err:
            raise NetLibError('Error connecting to "%s": %s' % (self.host, err))
        self.connection = connection

    def settimeout(self, n):
        self.connection.settimeout(n)

    def gettimeout(self):
        self.connection.gettimeout()

    def close(self):
        """
            Does a hard close of the socket, i.e. a shutdown, followed by a close.
        """
        try:
            if self.ssl_established:
                self.connection.shutdown()
            else:
                self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
        except (socket.error, SSL.Error):
            # Socket probably already closed
            pass


class BaseHandler:
    """
        The instantiator is expected to call the handle() and finish() methods.
    """
    rbufsize = -1
    wbufsize = -1
    def __init__(self, connection, client_address, server):
        self.connection = connection
        self.rfile = FileLike(self.connection.makefile('rb', self.rbufsize))
        self.wfile = FileLike(self.connection.makefile('wb', self.wbufsize))

        self.client_address = client_address
        self.server = server
        self.finished = False
        self.ssl_established = False

    def convert_to_ssl(self, cert, key, method=SSLv23_METHOD, options=None):
        """
            method: One of SSLv2_METHOD, SSLv3_METHOD, SSLv23_METHOD, or TLSv1_METHOD
        """
        ctx = SSL.Context(method)
        if not options is None:
            ctx.set_options(options)
        ctx.set_tlsext_servername_callback(self.handle_sni)
        ctx.use_privatekey_file(key)
        ctx.use_certificate_file(cert)
        self.connection = SSL.Connection(ctx, self.connection)
        self.ssl_established = True
        self.connection.set_accept_state()
        # SNI callback happens during do_handshake()
        try:
            self.connection.do_handshake()
        except SSL.Error, v:
            raise NetLibError("SSL handshake error: %s"%str(v))
        self.rfile = FileLike(self.connection)
        self.wfile = FileLike(self.connection)

    def finish(self):
        self.finished = True
        try:
            if not getattr(self.wfile, "closed", False):
                self.wfile.flush()
            self.close()
            self.wfile.close()
            self.rfile.close()
        except socket.error:
            # Remote has disconnected
            pass

    def handle_sni(self, connection):
        """
            Called if the client has given a server name indication.

            Server name can be retrieved like this:

                connection.get_servername()

            And you can specify the connection keys as follows:

                new_context = Context(TLSv1_METHOD)
                new_context.use_privatekey(key)
                new_context.use_certificate(cert)
                connection.set_context(new_context)
        """
        pass

    def handle(self): # pragma: no cover
        raise NotImplementedError

    def close(self):
        """
            Does a hard close of the socket, i.e. a shutdown, followed by a close.
        """
        try:
            if self.ssl_established:
                self.connection.shutdown()
            else:
                self.connection.shutdown(socket.SHUT_RDWR)
        except (socket.error, SSL.Error), v:
            # Socket probably already closed
            pass
        self.connection.close()


class TCPServer:
    request_queue_size = 20
    def __init__(self, server_address):
        self.server_address = server_address
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()
        self.port = self.server_address[1]
        self.socket.listen(self.request_queue_size)

    def request_thread(self, request, client_address):
        try:
            self.handle_connection(request, client_address)
            request.close()
        except:
            self.handle_error(request, client_address)
            request.close()

    def serve_forever(self, poll_interval=0.1):
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                r, w, e = select.select([self.socket], [], [], poll_interval)
                if self.socket in r:
                    try:
                        request, client_address = self.socket.accept()
                    except socket.error:
                        return
                    try:
                        t = threading.Thread(
                                target = self.request_thread,
                                args = (request, client_address)
                            )
                        t.setDaemon(1)
                        t.start()
                    except:
                        self.handle_error(request, client_address)
                        request.close()
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def shutdown(self):
        self.__shutdown_request = True
        self.__is_shut_down.wait()
        self.socket.close()
        self.handle_shutdown()

    def handle_error(self, request, client_address, fp=sys.stderr):
        """
            Called when handle_connection raises an exception.
        """
        # If a thread has persisted after interpreter exit, the module might be
        # none.
        if traceback:
            exc = traceback.format_exc()
            print >> fp, '-'*40
            print >> fp, "Error in processing of request from %s:%s"%client_address
            print >> fp, exc
            print >> fp, '-'*40

    def handle_connection(self, request, client_address): # pragma: no cover
        """
            Called after client connection.
        """
        raise NotImplementedError

    def handle_shutdown(self):
        """
            Called after server shutdown.
        """
        pass
