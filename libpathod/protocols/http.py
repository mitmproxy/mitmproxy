from netlib import tcp, http, wsgi
from netlib.http import http1
from .. import version, app, language, utils, log

class HTTPProtocol:

    def __init__(self, pathod_handler):
        self.pathod_handler = pathod_handler

    def make_error_response(self, reason, body):
        return language.http.make_error_response(reason, body)

    def handle_http_app(self, method, path, headers, content, lg):
        """
            Handle a request to the built-in app.
        """
        if self.pathod_handler.server.noweb:
            crafted = self.pathod_handler.make_http_error_response("Access Denied")
            language.serve(crafted, self.pathod_handler.wfile, self.pathod_handler.settings)
            return None, dict(
                type="error",
                msg="Access denied: web interface disabled"
            )
        lg("app: %s %s" % (method, path))
        req = wsgi.Request("http", method, path, headers, content)
        flow = wsgi.Flow(self.pathod_handler.address, req)
        sn = self.pathod_handler.connection.getsockname()
        a = wsgi.WSGIAdaptor(
            self.pathod_handler.server.app,
            sn[0],
            self.pathod_handler.server.address.port,
            version.NAMEVERSION
        )
        a.serve(flow, self.pathod_handler.wfile)
        return self.pathod_handler.handle_http_request, None

    def handle_http_connect(self, connect, lg):
        """
            Handle a CONNECT request.
        """
        http1.read_headers(self.pathod_handler.rfile)
        self.pathod_handler.wfile.write(
            'HTTP/1.1 200 Connection established\r\n' +
            ('Proxy-agent: %s\r\n' % version.NAMEVERSION) +
            '\r\n'
        )
        self.pathod_handler.wfile.flush()
        if not self.pathod_handler.server.ssloptions.not_after_connect:
            try:
                cert, key, chain_file_ = self.pathod_handler.server.ssloptions.get_cert(
                    connect[0]
                )
                self.pathod_handler.convert_to_ssl(
                    cert,
                    key,
                    handle_sni=self.pathod_handler._handle_sni,
                    request_client_cert=self.pathod_handler.server.ssloptions.request_client_cert,
                    cipher_list=self.pathod_handler.server.ssloptions.ciphers,
                    method=self.pathod_handler.server.ssloptions.ssl_version,
                    alpn_select=self.pathod_handler.server.ssloptions.alpn_select,
                )
            except tcp.NetLibError as v:
                s = str(v)
                lg(s)
                return None, dict(type="error", msg=s)
        return self.pathod_handler.handle_http_request, None

    def read_request(self, lg):
        line = http1.get_request_line(self.pathod_handler.rfile)
        if not line:
            # Normal termination
            return dict()

        m = utils.MemBool()
        if m(http1.parse_init_connect(line)):
            return dict(next_handle=self.handle_http_connect(m.v, lg))
        elif m(http1.parse_init_proxy(line)):
            method, _, _, _, path, httpversion = m.v
        elif m(http1.parse_init_http(line)):
            method, path, httpversion = m.v
        else:
            s = "Invalid first line: %s" % repr(line)
            lg(s)
            return dict(errors=dict(type="error", msg=s))

        headers = http1.read_headers(self.pathod_handler.rfile)
        if headers is None:
            s = "Invalid headers"
            lg(s)
            return dict(errors=dict(type="error", msg=s))

        try:
            body = http1.read_http_body(
                self.pathod_handler.rfile,
                headers,
                None,
                method,
                None,
                True,
            )
        except http.HttpError as s:
            s = str(s)
            lg(s)
            return dict(errors=dict(type="error", msg=s))

        return dict(
            method=method,
            path=path,
            headers=headers,
            body=body,
            httpversion=httpversion)
