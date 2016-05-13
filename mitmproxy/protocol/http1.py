from __future__ import (absolute_import, print_function, division)


from netlib.http import http1

from .http import _HttpTransmissionLayer, HttpLayer
from ..models import HTTPRequest, HTTPResponse


class Http1Layer(_HttpTransmissionLayer):

    def __init__(self, ctx, mode):
        super(Http1Layer, self).__init__(ctx)
        self.mode = mode

    def read_request(self):
        req = http1.read_request(self.client_conn.rfile, body_size_limit=self.config.body_size_limit)
        return HTTPRequest.wrap(req)

    def read_request_body(self, request):
        expected_size = http1.expected_http_body_size(request)
        return http1.read_body(self.client_conn.rfile, expected_size, self.config.body_size_limit)

    def send_request(self, request):
        self.server_conn.wfile.write(http1.assemble_request(request))
        self.server_conn.wfile.flush()

    def read_response_headers(self):
        resp = http1.read_response_head(self.server_conn.rfile)
        return HTTPResponse.wrap(resp)

    def read_response_body(self, request, response):
        expected_size = http1.expected_http_body_size(request, response)
        return http1.read_body(self.server_conn.rfile, expected_size, self.config.body_size_limit)

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
        layer = HttpLayer(self, self.mode)
        layer()
