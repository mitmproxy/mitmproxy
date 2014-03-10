import select, socket, threading, sys, time, traceback
from OpenSSL import SSL
import certutils


EINTR = 4

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
            except SSL.SysCallError as e:
                if e.args == (-1, 'Unexpected EOF'):
                    break
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


class Address(object):
    """
    This class wraps an IPv4/IPv6 tuple to provide named attributes and ipv6 information.
    """
    def __init__(self, address, use_ipv6=False):
        self.address = tuple(address)
        self.use_ipv6 = use_ipv6

    @classmethod
    def wrap(cls, t):
        if isinstance(t, cls):
            return t
        else:
            return cls(t)

    def __call__(self):
        return self.address

    @property
    def host(self):
        return self.address[0]

    @property
    def port(self):
        return self.address[1]

    @property
    def use_ipv6(self):
        return self.family == socket.AF_INET6

    @use_ipv6.setter
    def use_ipv6(self, b):
        self.family = socket.AF_INET6 if b else socket.AF_INET

    def __eq__(self, other):
        other = Address.wrap(other)
        return (self.address, self.family) == (other.address, other.family)


class _Connection(object):
    def get_current_cipher(self):
        if not self.ssl_established:
            return None
        c = SSL._lib.SSL_get_current_cipher(self.connection._ssl)
        name = SSL._native(SSL._ffi.string(SSL._lib.SSL_CIPHER_get_name(c)))
        bits = SSL._lib.SSL_CIPHER_get_bits(c, SSL._ffi.NULL)
        version = SSL._native(SSL._ffi.string(SSL._lib.SSL_CIPHER_get_version(c)))
        return name, bits, version

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
            #Section 4.2.2.13 of RFC 1122 tells us that a close() with any
            # pending readable data could lead to an immediate RST being sent.
            #http://ia600609.us.archive.org/22/items/TheUltimateSo_lingerPageOrWhyIsMyTcpNotReliable/the-ultimate-so_linger-page-or-why-is-my-tcp-not-reliable.html
            while self.connection.recv(4096): # pragma: no cover
                pass
            self.connection.close()
        except (socket.error, SSL.Error, IOError):
            # Socket probably already closed
            pass


class TCPClient(_Connection):
    rbufsize = -1
    wbufsize = -1
    def __init__(self, address, source_address=None):
        self.address = Address.wrap(address)
        self.source_address = Address.wrap(source_address) if source_address else None
        self.connection, self.rfile, self.wfile = None, None, None
        self.cert = None
        self.ssl_established = False
        self.sni = None

    def convert_to_ssl(self, cert=None, sni=None, method=TLSv1_METHOD, options=None, cipher_list=None):
        """
            cert: Path to a file containing both client cert and private key.
        """
        context = SSL.Context(method)
        if cipher_list:
            try:
                context.set_cipher_list(cipher_list)
            except SSL.Error, v:
                raise NetLibError("SSL cipher specification error: %s"%str(v))
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
            self.sni = sni
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
            connection = socket.socket(self.address.family, socket.SOCK_STREAM)
            if self.source_address:
                connection.bind(self.source_address())
            connection.connect(self.address())
            self.rfile = Reader(connection.makefile('rb', self.rbufsize))
            self.wfile = Writer(connection.makefile('wb', self.wbufsize))
        except (socket.error, IOError), err:
            raise NetLibError('Error connecting to "%s": %s' % (self.address.host, err))
        self.connection = connection

    def settimeout(self, n):
        self.connection.settimeout(n)

    def gettimeout(self):
        return self.connection.gettimeout()


class BaseHandler(_Connection):
    """
        The instantiator is expected to call the handle() and finish() methods.

    """
    rbufsize = -1
    wbufsize = -1

    def __init__(self, connection, address, server):
        self.connection = connection
        self.address = Address.wrap(address)
        self.server = server
        self.rfile = Reader(self.connection.makefile('rb', self.rbufsize))
        self.wfile = Writer(self.connection.makefile('wb', self.wbufsize))

        self.finished = False
        self.ssl_established = False
        self.clientcert = None

    def convert_to_ssl(self, cert, key, 
                        method=SSLv23_METHOD, options=None, handle_sni=None, 
                        request_client_cert=False, cipher_list=None, dhparams=None
                    ):
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
            try:
                ctx.set_cipher_list(cipher_list)
            except SSL.Error, v:
                raise NetLibError("SSL cipher specification error: %s"%str(v))
        if handle_sni:
            # SNI callback happens during do_handshake()
            ctx.set_tlsext_servername_callback(handle_sni)
        ctx.use_privatekey(key)
        ctx.use_certificate(cert.x509)
        if dhparams:
            SSL._lib.SSL_CTX_set_tmp_dh(ctx._context, dhparams)
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

    def handle(self): # pragma: no cover
        raise NotImplementedError

    def settimeout(self, n):
        self.connection.settimeout(n)



class TCPServer(object):
    request_queue_size = 20
    def __init__(self, address):
        self.address = Address.wrap(address)
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False
        self.socket = socket.socket(self.address.family, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.address())
        self.address = Address.wrap(self.socket.getsockname())
        self.socket.listen(self.request_queue_size)

    def connection_thread(self, connection, client_address):
        client_address = Address(client_address)
        try:
            self.handle_client_connection(connection, client_address)
        except:
            self.handle_error(connection, client_address)
        finally:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except:
                pass
            connection.close()

    def serve_forever(self, poll_interval=0.1):
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                try:
                    r, w, e = select.select([self.socket], [], [], poll_interval)
                except select.error, ex: # pragma: no cover
                        if ex[0] == EINTR:
                            continue
                        else:
                            raise  
                if self.socket in r:
                    connection, client_address = self.socket.accept()
                    t = threading.Thread(
                            target = self.connection_thread,
                            args = (connection, client_address),
                            name = "ConnectionThread (%s:%s -> %s:%s)" %
                                   (client_address[0], client_address[1],
                                    self.address.host, self.address.port)
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
            Called when handle_client_connection raises an exception.
        """
        # If a thread has persisted after interpreter exit, the module might be
        # none.
        if traceback:
            exc = traceback.format_exc()
            print >> fp, '-'*40
            print >> fp, "Error in processing of request from %s:%s" % (client_address.host, client_address.port)
            print >> fp, exc
            print >> fp, '-'*40

    def handle_client_connection(self, conn, client_address):  # pragma: no cover
        """
            Called after client connection.
        """
        raise NotImplementedError

    def handle_shutdown(self):
        """
            Called after server shutdown.
        """
        pass
