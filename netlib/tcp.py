import select, socket, threading, traceback, sys
from OpenSSL import SSL


class NetLibError(Exception): pass


class FileLike:
    def __init__(self, o):
        self.o = o

    def __getattr__(self, attr):
        return getattr(self.o, attr)

    def flush(self):
        pass

    def read(self, length):
        result = ''
        while len(result) < length:
            try:
                data = self.o.read(length)
            except SSL.ZeroReturnError:
                break
            if not data:
                break
            result += data
        return result

    def write(self, v):
        self.o.sendall(v)

    def readline(self, size = None):
        result = ''
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
                if ch == '\n':
                    break
        return result


class TCPClient:
    def __init__(self, ssl, host, port, clientcert):
        self.ssl, self.host, self.port, self.clientcert = ssl, host, port, clientcert
        self.connection, self.rfile, self.wfile = None, None, None
        self.cert = None
        self.connect()

    def connect(self):
        try:
            addr = socket.gethostbyname(self.host)
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.ssl:
                context = SSL.Context(SSL.SSLv23_METHOD)
                if self.clientcert:
                    context.use_certificate_file(self.clientcert)
                server = SSL.Connection(context, server)
            server.connect((addr, self.port))
            if self.ssl:
                self.cert = server.get_peer_certificate()
                self.rfile, self.wfile = FileLike(server), FileLike(server)
            else:
                self.rfile, self.wfile = server.makefile('rb'), server.makefile('wb')
        except socket.error, err:
            raise NetLibError('Error connecting to "%s": %s' % (self.host, err))
        self.connection = server


class BaseHandler:
    rbufsize = -1
    wbufsize = 0
    def __init__(self, connection, client_address, server):
        self.connection = connection
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.connection.makefile('wb', self.wbufsize)

        self.client_address = client_address
        self.server = server
        self.handle()
        self.finish()

    def convert_to_ssl(self, cert, key):
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_privatekey_file(key)
        ctx.use_certificate_file(cert)
        self.connection = SSL.Connection(ctx, self.connection)
        self.connection.set_accept_state()
        self.rfile = FileLike(self.connection)
        self.wfile = FileLike(self.connection)

    def finish(self):
        try:
            if not getattr(self.wfile, "closed", False):
                self.wfile.flush()
            self.connection.close()
            self.wfile.close()
            self.rfile.close()
        except IOError: # pragma: no cover
            pass

    def handle(self): # pragma: no cover
        raise NotImplementedError


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
        self.socket.listen(self.request_queue_size)
        self.port = self.socket.getsockname()[1]

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
        print >> fp, '-'*40
        print >> fp, "Error processing of request from %s:%s"%client_address
        print >> fp, traceback.format_exc()
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
