from .rawtcp import TcpLayer
from .tls import TlsLayer


class RootContext(object):
    """
    The outmost context provided to the root layer.
    As a consequence, every layer has .client_conn, .channel, .next_layer() and .config.
    """

    def __init__(self, client_conn, config, channel):
        self.client_conn = client_conn  # Client Connection
        self.channel = channel  # provides .ask() method to communicate with FlowMaster
        self.config = config  # Proxy Configuration

    def next_layer(self, top_layer):
        """
        This function determines the next layer in the protocol stack.
        :param top_layer: the current top layer
        :return: The next layer.
        """

        d = top_layer.client_conn.rfile.peek(1)

        if not d:
            return
        # TLS ClientHello magic, see http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
        if d[0] == "\x16":
            layer = TlsLayer(top_layer, True, True)
        else:
            layer = TcpLayer(top_layer)
        return layer
