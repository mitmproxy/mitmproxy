import select, socket, threading, sys, time, traceback
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
class NetLibDisconnect(NetLibError): pass
class NetLibTimeout(NetLibError): pass
class NetLibSSLError(NetLibError): pass


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
        return "".join(self._log)

    def add_log(self, v):
        if self.is_logging():
            self._log.append(v)

    def reset_timestamps(self):
        self.first_byte_timestamp = None


class Writer(_FileLike):
    def flush(self):
        """
            May raise NetLibDisconnect
        """
        if hasattr(self.o, "flush"):
            try:
                self.o.flush()
            except (socket.error, IOError), v:
                raise NetLibDisconnect(str(v))

    def write(self, v):
        """
            May raise NetLibDisconnect
        """
        if v:
            try:
                if hasattr(self.o, "sendall"):
                    self.add_log(v)
                    return self.o.sendall(v)
                else:
                    r = self.o.write(v)
                    self.add_log(v[:r])
                    return r
            except (SSL.Error, socket.error), v:
                raise NetLibDisconnect(str(v))


class Reader(_FileLike):
    def read(self, length):
        """
            If length is -1, we read until connection closes.
        """
        result = ''
        start = time.time()
        while length == -1 or length > 0:
            if length == -1 or length > self.BLOCKSIZE:
                rlen = self.BLOCKSIZE
            else:
                rlen = length
            try:
                data = self.o.read(rlen)
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
            except SSL.SysCallError:
                raise NetLibDisconnect
            except SSL.Error, v:
                raise NetLibSSLError(v.message)
            self.first_byte_timestamp = self.first_byte_timestamp or time.time()
            if not data:
                break
            result += data
            if length != -1:
                length -= len(data)
        self.add_log(result)
        return result

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
    def __init__(self, host, port, source_address=None, use_ipv6=False):
        self.host, self.port = host, port
        self.source_address = source_address
        self.use_ipv6 = use_ipv6
        self.connection, self.rfile, self.wfile = None, None, None
        self.cert = None
        self.ssl_established = False

    def convert_to_ssl(self, cert=None, sni=None, method=TLSv1_METHOD, options=None):
        """
            cert: Path to a file containing both client cert and private key.
        """
        context = SSL.Context(method)
        if options is not None:
            context.set_options(options)
        if cert:
            try:
                context.use_privatekey_file(cert)
                context.use_certificate_file(cert)
            except SSL.Error, v:
                raise NetLibError("SSL client certificate error: %s"%str(v))
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
        self.rfile.set_descriptor(self.connection)
        self.wfile.set_descriptor(self.connection)

    def connect(self):
        try:
            connection = socket.socket(socket.AF_INET6 if self.use_ipv6 else socket.AF_INET, socket.SOCK_STREAM)
            if self.source_address:
                connection.bind(self.source_address)
            connection.connect((self.host, self.port))
            self.rfile = Reader(connection.makefile('rb', self.rbufsize))
            self.wfile = Writer(connection.makefile('wb', self.wbufsize))
        except (socket.error, IOError), err:
            raise NetLibError('Error connecting to "%s": %s' % (self.host, err))
        self.connection = connection

    def settimeout(self, n):
        self.connection.settimeout(n)

    def gettimeout(self):
        return self.connection.gettimeout()

    def close(self):
        """
            Does a hard close of the socket, i.e. a shutdown, followed by a close.
        """
        try:
            if self.ssl_established:
                self.connection.shutdown()
                self.connection.sock_shutdown(socket.SHUT_WR)
            else:
                self.connection.shutdown(socket.SHUT_WR)
            #Section 4.2.2.13 of RFC 1122 tells us that a close() with any pending readable data could lead to an immediate RST being sent.
            #http://ia600609.us.archive.org/22/items/TheUltimateSo_lingerPageOrWhyIsMyTcpNotReliable/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable.html
            while self.connection.recv(4096):
                pass
            self.connection.close()
        except (socket.error, SSL.Error, IOError):
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
        self.rfile = Reader(self.connection.makefile('rb', self.rbufsize))
        self.wfile = Writer(self.connection.makefile('wb', self.wbufsize))

        self.client_address = client_address
        self.server = server
        self.finished = False
        self.ssl_established = False

        self.clientcert = None

    def convert_to_ssl(self, cert, key, method=SSLv23_METHOD, options=None, handle_sni=None, request_client_cert=False, cipher_list=None):
        """
            cert: A certutils.SSLCert object.
            method: One of SSLv2_METHOD, SSLv3_METHOD, SSLv23_METHOD, or TLSv1_METHOD
            handle_sni: SNI handler, should take a connection object. Server
            name can be retrieved like this:

                            connection.get_servername()

                        And you can specify the connection keys as follows:

                            new_context = Context(TLSv1_METHOD)
                            new_context.use_privatekey(key)
                            new_context.use_certificate(cert)
                            connection.set_context(new_context)

            The request_client_cert argument requires some explanation. We're
            supposed to be able to do this with no negative effects - if the
            client has no cert to present, we're notified and proceed as usual.
            Unfortunately, Android seems to have a bug (tested on 4.2.2) - when
            an Android client is asked to present a certificate it does not
            have, it hangs up, which is frankly bogus. Some time down the track
            we may be able to make the proper behaviour the default again, but
            until then we're conservative.
        """
        ctx = SSL.Context(method)
        if not options is None:
            ctx.set_options(options)
        if cipher_list:
            ctx.set_cipher_list(cipher_list)
        if handle_sni:
            # SNI callback happens during do_handshake()
            ctx.set_tlsext_servername_callback(handle_sni)
        ctx.use_privatekey_file(key)
        ctx.use_certificate(cert.x509)
        if request_client_cert:
            def ver(*args):
                self.clientcert = certutils.SSLCert(args[1])
                # Return true to prevent cert verification error
                return True
            ctx.set_verify(SSL.VERIFY_PEER, ver)
        self.connection = SSL.Connection(ctx, self.connection)
        self.ssl_established = True
        self.connection.set_accept_state()
        try:
            self.connection.do_handshake()
        except SSL.Error, v:
            raise NetLibError("SSL handshake error: %s"%str(v))
        self.rfile.set_descriptor(self.connection)
        self.wfile.set_descriptor(self.connection)

    def finish(self):
        self.finished = True
        try:
            if not getattr(self.wfile, "closed", False):
                self.wfile.flush()
            self.close()
            self.wfile.close()
            self.rfile.close()
        except (socket.error, NetLibDisconnect):
            # Remote has disconnected
            pass

    def handle(self): # pragma: no cover
        raise NotImplementedError

    def settimeout(self, n):
        self.connection.settimeout(n)

    def close(self):
        """
            Does a hard close of the socket, i.e. a shutdown, followed by a close.
        """
        try:
            if self.ssl_established:
                self.connection.shutdown()
                self.connection.sock_shutdown(socket.SHUT_WR)
            else:
                self.connection.shutdown(socket.SHUT_WR)
            # Section 4.2.2.13 of RFC 1122 tells us that a close() with any
            # pending readable data could lead to an immediate RST being sent.
            # http://ia600609.us.archive.org/22/items/TheUltimateSo_lingerPageOrWhyIsMyTcpNotReliable/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable.html
            while self.connection.recv(4096):
                pass
        except (socket.error, SSL.Error):
            # Socket probably already closed
            pass
        self.connection.close()


class TCPServer:
    request_queue_size = 20
    def __init__(self, server_address, use_ipv6=False):
        self.server_address = server_address
        self.use_ipv6 = use_ipv6
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False
        self.socket = socket.socket(socket.AF_INET6 if self.use_ipv6 else socket.AF_INET, socket.SOCK_STREAM)
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
                try:
                    r, w, e = select.select([self.socket], [], [], poll_interval)
                except select.error, ex:
                        if ex[0] == 4:
                            continue
                        else:
                            raise  
                if self.socket in r:
                    request, client_address = self.socket.accept()
                    t = threading.Thread(
                            target = self.request_thread,
                            args = (request, client_address)
                        )
                    t.setDaemon(1)
                    t.start()
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
