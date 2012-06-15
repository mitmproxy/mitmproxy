import select, socket, threading

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

    def finish(self):
        try:
            if not getattr(self.wfile, "closed", False):
                self.wfile.flush()
            self.connection.close()
            self.wfile.close()
            self.rfile.close()
        except IOError:
            pass

    def handle(self):
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

    def fileno(self):
        return self.socket.fileno()

    def request_thread(self, request, client_address):
        try:
            self.handle_connection(request, client_address)
            request.close()
        except:
            self.handle_error(request, client_address)
            request.close()

    def serve_forever(self, poll_interval=0.5):
        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                r, w, e = select.select([self], [], [], poll_interval)
                if self in r:
                    try:
                        request, client_address = self.socket.accept()
                    except socket.error:
                        return
                    try:
                        t = threading.Thread(target = self.request_thread,
                                             args = (request, client_address))
                        t.setDaemon (1)
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

    def handle_error(self, request, client_address):
        print '-'*40
        print 'Exception happened during processing of request from',
        print client_address
        import traceback
        traceback.print_exc() # XXX But this goes to stderr!
        print '-'*40

    def handle_connection(self, request, client_address):
        raise NotImplementedError
