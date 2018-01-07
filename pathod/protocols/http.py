from mitmproxy import version
from mitmproxy import exceptions
from mitmproxy.net.http import http1
from .. import language


class HTTPProtocol:
    def __init__(self, pathod_handler):
        self.pathod_handler = pathod_handler

    def make_error_response(self, reason, body):
        return language.http.make_error_response(reason, body)

    def handle_http_connect(self, connect, lg):
        """
            Handle a CONNECT request.
        """

        self.pathod_handler.wfile.write(
            b'HTTP/1.1 200 Connection established\r\n' +
            (b'Proxy-agent: %s\r\n' % version.PATHOD.encode()) +
            b'\r\n'
        )
        self.pathod_handler.wfile.flush()
        if not self.pathod_handler.server.ssloptions.not_after_connect:
            try:
                cert, key, chain_file_ = self.pathod_handler.server.ssloptions.get_cert(
                    connect[0].encode()
                )
                self.pathod_handler.convert_to_tls(
                    cert,
                    key,
                    handle_sni=self.pathod_handler.handle_sni,
                    request_client_cert=self.pathod_handler.server.ssloptions.request_client_cert,
                    cipher_list=self.pathod_handler.server.ssloptions.ciphers,
                    method=self.pathod_handler.server.ssloptions.ssl_version,
                    options=self.pathod_handler.server.ssloptions.ssl_options,
                    alpn_select=self.pathod_handler.server.ssloptions.alpn_select,
                )
            except exceptions.TlsException as v:
                s = str(v)
                lg(s)
                return None, dict(type="error", msg=s)
        return self.pathod_handler.handle_http_request, None

    def read_request(self, lg=None):
        return http1.read_request(self.pathod_handler.rfile)
