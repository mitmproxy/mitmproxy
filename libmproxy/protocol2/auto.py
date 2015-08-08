from __future__ import (absolute_import, print_function, division)
from .layer import Layer


class AutoLayer(Layer):
    def __call__(self):
        d = self.client_conn.rfile.peek(1)

        if not d:
            return
        # TLS ClientHello magic, see http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
        if d[0] == "\x16":
            layer = TlsLayer(self, True, True)
        else:
            layer = TcpLayer(self)
        for m in layer():
            yield m

from .rawtcp import TcpLayer
from .tls import TlsLayer
