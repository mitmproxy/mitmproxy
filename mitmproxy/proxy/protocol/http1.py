from mitmproxy import http
from mitmproxy.proxy.protocol import http as httpbase
from mitmproxy.net.http import http1
from mitmproxy.utils import human


class Http1Layer(httpbase._HttpTransmissionLayer):

    def __init__(self, ctx, mode):
        super().__init__(ctx)
        self.mode = mode

    def read_request_headers(self, flow):
        return http.HTTPRequest.wrap(
            http1.read_request_head(self.client_conn.rfile)
        )

    def read_request_body(self, request):
        expected_size = http1.expected_http_body_size(request)
        return http1.read_body(
            self.client_conn.rfile,
            expected_size,
            human.parse_size(self.config.options.body_size_limit)
        )

    def send_request_headers(self, request):
        headers = http1.assemble_request_head(request)
        self.server_conn.wfile.write(headers)
        self.server_conn.wfile.flush()

    def send_request_body(self, request, chunks):
        for chunk in http1.assemble_body(request.headers, chunks):
            self.server_conn.wfile.write(chunk)
            self.server_conn.wfile.flush()

    def send_request(self, request):
        self.server_conn.wfile.write(http1.assemble_request(request))
        self.server_conn.wfile.flush()

    def read_response_headers(self):
        resp = http1.read_response_head(self.server_conn.rfile)
        return http.HTTPResponse.wrap(resp)

    def read_response_body(self, request, response):
        expected_size = http1.expected_http_body_size(request, response)
        return http1.read_body(
            self.server_conn.rfile,
            expected_size,
            human.parse_size(self.config.options.body_size_limit)
        )

    def send_response_headers(self, response):
        raw = http1.assemble_response_head(response)
        self.client_conn.wfile.write(raw)
        self.client_conn.wfile.flush()

    def send_response_body(self, response, chunks):
        for chunk in http1.assemble_body(response.headers, chunks):
            self.client_conn.wfile.write(chunk)
            self.client_conn.wfile.flush()

    def check_close_connection(self, flow):
        request_close = http1.connection_close(
            flow.request.http_version,
            flow.request.headers
        )
        response_close = http1.connection_close(
            flow.response.http_version,
            flow.response.headers
        )
        read_until_eof = http1.expected_http_body_size(flow.request, flow.response) == -1
        close_connection = request_close or response_close or read_until_eof
        if flow.request.first_line_format == "authority" and flow.response.status_code == 200:
            # Workaround for https://github.com/mitmproxy/mitmproxy/issues/313:
            # Charles Proxy sends a CONNECT response with HTTP/1.0
            # and no Content-Length header

            return False
        return close_connection

    def __call__(self):
        layer = httpbase.HttpLayer(self, self.mode)
        layer()
