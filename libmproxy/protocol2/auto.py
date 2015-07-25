from __future__ import (absolute_import, print_function, division, unicode_literals)
from .layer import Layer


class AutoLayer(Layer):
    def __call__(self):
        d = self.client_conn.rfile.peek(1)

        # TLS ClientHello magic, see http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
        if d[0] == "\x16":
            layer = SslLayer(self, True, True)
        else:
            layer = TcpLayer(self)
        for m in layer():
            yield m

from .rawtcp import TcpLayer
from .ssl import SslLayer
