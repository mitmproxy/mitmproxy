import threading, Queue, cStringIO
import tcp, certutils
import OpenSSL

class ServerThread(threading.Thread):
    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class ServerTestBase:
    ssl = None
    handler = None
    addr = ("localhost", 0)

    @classmethod
    def setupAll(cls):
        cls.q = Queue.Queue()
        s = cls.makeserver()
        cls.port = s.address.port
        cls.server = ServerThread(s)
        cls.server.start()

    @classmethod
    def makeserver(cls):
        return TServer(cls.ssl, cls.q, cls.handler, cls.addr)

    @classmethod
    def teardownAll(cls):
        cls.server.shutdown()

    @property
    def last_handler(self):
        return self.server.server.last_handler


class TServer(tcp.TCPServer):
    def __init__(self, ssl, q, handler_klass, addr):
        """
            ssl: A {cert, key, v3_only} dict.
        """
        tcp.TCPServer.__init__(self, addr)
        self.ssl, self.q = ssl, q
        self.handler_klass = handler_klass
        self.last_handler = None



    def handle_client_connection(self, request, client_address):
        h = self.handler_klass(request, client_address, self)
        self.last_handler = h
        if self.ssl:
            cert = certutils.SSLCert.from_pem(
                file(self.ssl["cert"], "rb").read()
            )
            raw = file(self.ssl["key"], "rb").read()
            key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, raw)
            if self.ssl["v3_only"]:
                method = tcp.SSLv3_METHOD
                options = tcp.OP_NO_SSLv2|tcp.OP_NO_TLSv1
            else:
                method = tcp.SSLv23_METHOD
                options = None
            h.convert_to_ssl(
                cert, key,
                method = method,
                options = options,
                handle_sni = getattr(h, "handle_sni", None),
                request_client_cert = self.ssl["request_client_cert"],
                cipher_list = self.ssl.get("cipher_list", None)
            )
        h.handle()
        h.finish()

    def handle_error(self, request, client_address):
        s = cStringIO.StringIO()
        tcp.TCPServer.handle_error(self, request, client_address, s)
        self.q.put(s.getvalue())
