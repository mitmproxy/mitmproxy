from __future__ import (absolute_import, print_function, division)

from .layer import Layer, ServerConnectionMixin
from libmproxy import version
from libmproxy.exceptions import InvalidCredentials
from libmproxy.protocol.http import HTTPFlow
from libmproxy.protocol.http_wrappers import HTTPResponse
from libmproxy.protocol2.http_protocol_mock import HTTP1
from netlib import tcp
from netlib.http import status_codes
from netlib import odict


def send_http_error_response(status_code, message, headers=odict.ODictCaseless()):
    response = status_codes.RESPONSES.get(status_code, "Unknown")
    body = """
        <html>
            <head>
                <title>%d %s</title>
            </head>
            <body>%s</body>
        </html>
    """.strip() % (status_code, response, message)

    headers["Server"] = [version.NAMEVERSION]
    headers["Connection"] = ["close"]
    headers["Content-Length"] = [len(body)]
    headers["Content-Type"] = ["text/html"]

    resp = HTTPResponse(
        (1, 1),  # if HTTP/2 is used, this value is ignored anyway
        status_code,
        response,
        headers,
        body,
    )

    protocol = self.c.client_conn.protocol or http1.HTTP1Protocol(self.c.client_conn)
    self.c.client_conn.send(protocol.assemble(resp))

class HttpLayer(Layer, ServerConnectionMixin):
    """
    HTTP 1 Layer
    """

    def __init__(self, ctx):
        super(HttpLayer, self).__init__(ctx)
        self.skip_authentication = False

    def __call__(self):
        while True:
            flow = HTTPFlow(self.client_conn, self.server_conn)
            try:
                request = HTTP1.read_request(
                    self.client_conn,
                    body_size_limit=self.c.config.body_size_limit
                )
            except tcp.NetLibError:
                # don't throw an error for disconnects that happen
                # before/between requests.
                return

            self.c.log("request", "debug", [repr(request)])

            self.check_authentication(request)

            if self.mode == "regular" and request.form_in == "authority":
                raise NotImplementedError



            ret = self.process_request(flow, request)
            if ret is True:
                continue
            if ret is False:
                return

    def check_authentication(self, request):
        if self.config.authenticator:
            if self.config.authenticator.authenticate(request.headers):
                self.config.authenticator.clean(request.headers)
            else:
                self.send_error()
                raise InvalidCredentials("Proxy Authentication Required")
                raise http.HttpAuthenticationError(
                    self.c.config.authenticator.auth_challenge_headers())
        return request.headers

    def send_error(self, code, message, headers):
        pass