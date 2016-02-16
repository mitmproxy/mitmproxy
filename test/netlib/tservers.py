from __future__ import (absolute_import, print_function, division)

import threading
from six.moves import queue
from io import StringIO
import OpenSSL

from netlib import tcp
from netlib import tutils


class _ServerThread(threading.Thread):

    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class _TServer(tcp.TCPServer):

    def __init__(self, ssl, q, handler_klass, addr):
        """
            ssl: A dictionary of SSL parameters:

                    cert, key, request_client_cert, cipher_list,
                    dhparams, v3_only
        """
        tcp.TCPServer.__init__(self, addr)

        if ssl is True:
            self.ssl = dict()
        elif isinstance(ssl, dict):
            self.ssl = ssl
        else:
            self.ssl = None

        self.q = q
        self.handler_klass = handler_klass
        self.last_handler = None

    def handle_client_connection(self, request, client_address):
        h = self.handler_klass(request, client_address, self)
        self.last_handler = h
        if self.ssl is not None:
            cert = self.ssl.get(
                "cert",
                tutils.test_data.path("data/server.crt"))
            raw_key = self.ssl.get(
                "key",
                tutils.test_data.path("data/server.key"))
            key = OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM,
                open(raw_key, "rb").read())
            if self.ssl.get("v3_only", False):
                method = OpenSSL.SSL.SSLv3_METHOD
                options = OpenSSL.SSL.OP_NO_SSLv2 | OpenSSL.SSL.OP_NO_TLSv1
            else:
                method = OpenSSL.SSL.SSLv23_METHOD
                options = None
            h.convert_to_ssl(
                cert, key,
                method=method,
                options=options,
                handle_sni=getattr(h, "handle_sni", None),
                request_client_cert=self.ssl.get("request_client_cert", None),
                cipher_list=self.ssl.get("cipher_list", None),
                dhparams=self.ssl.get("dhparams", None),
                chain_file=self.ssl.get("chain_file", None),
                alpn_select=self.ssl.get("alpn_select", None)
            )
        h.handle()
        h.finish()

    def handle_error(self, connection, client_address, fp=None):
        s = StringIO()
        tcp.TCPServer.handle_error(self, connection, client_address, s)
        self.q.put(s.getvalue())


class ServerTestBase(object):
    ssl = None
    handler = None
    addr = ("localhost", 0)

    @classmethod
    def setup_class(cls):
        cls.q = queue.Queue()
        s = cls.makeserver()
        cls.port = s.address.port
        cls.server = _ServerThread(s)
        cls.server.start()

    @classmethod
    def makeserver(cls):
        return _TServer(cls.ssl, cls.q, cls.handler, cls.addr)

    @classmethod
    def teardown_class(cls):
        cls.server.shutdown()

    @property
    def last_handler(self):
        return self.server.server.last_handler
