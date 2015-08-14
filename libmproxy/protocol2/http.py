from __future__ import (absolute_import, print_function, division)

from .. import version
from ..exceptions import InvalidCredentials, HttpException, ProtocolException
from .layer import Layer, ServerConnectionMixin
from .messages import ChangeServer, Connect, Reconnect
from .http_proxy import HttpProxy, HttpUpstreamProxy
from libmproxy.protocol import KILL

from libmproxy.protocol.http import HTTPFlow
from libmproxy.protocol.http_wrappers import HTTPResponse, HTTPRequest
from libmproxy.protocol2.http_protocol_mock import HTTP1
from libmproxy.protocol2.tls import TlsLayer
from netlib import tcp
from netlib.http import status_codes
from netlib import odict


def make_error_response(status_code, message, headers=None):
    response = status_codes.RESPONSES.get(status_code, "Unknown")
    body = """
        <html>
            <head>
                <title>%d %s</title>
            </head>
            <body>%s</body>
        </html>
    """.strip() % (status_code, response, message)

    if not headers:
        headers = odict.ODictCaseless()
    headers["Server"] = [version.NAMEVERSION]
    headers["Connection"] = ["close"]
    headers["Content-Length"] = [len(body)]
    headers["Content-Type"] = ["text/html"]

    return HTTPResponse(
        (1, 1),  # FIXME: Should be a string.
        status_code,
        response,
        headers,
        body,
    )

def make_connect_request(address):
    return HTTPRequest(
        "authority", "CONNECT", None, address.host, address.port, None, (1,1),
        odict.ODictCaseless(), ""
    )

def make_connect_response(httpversion):
    headers = odict.ODictCaseless([
        ["Content-Length", "0"],
        ["Proxy-Agent", version.NAMEVERSION]
    ])
    return HTTPResponse(
        httpversion,
        200,
        "Connection established",
        headers,
        "",
    )


class HttpLayer(Layer, ServerConnectionMixin):
    """
    HTTP 1 Layer
    """

    def __init__(self, ctx):
        super(HttpLayer, self).__init__(ctx)
        if any(isinstance(l, HttpProxy) for l in self.layers):
            self.mode = "regular"
        elif any(isinstance(l, HttpUpstreamProxy) for l in self.layers):
            self.mode = "upstream"
        else:
            # also includes socks or reverse mode, which are handled similarly on this layer.
            self.mode = "transparent"

    def __call__(self):
        while True:
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

            # Handle Proxy Authentication
            self.authenticate(request)

            # Regular Proxy Mode: Handle CONNECT
            if self.mode == "regular" and request.form_in == "authority":
                self.server_address = (request.host, request.port)
                self.send_to_client(make_connect_response(request.httpversion))
                layer = self.ctx.next_layer(self)
                for message in layer():
                    if not self._handle_server_message(message):
                        yield message
                return

            # Make sure that the incoming request matches our expectations
            self.validate_request(request)

            flow = HTTPFlow(self.client_conn, self.server_conn)
            flow.request = request
            if not self.process_request_hook(flow):
                self.log("Connection killed", "info")
                return

            if not flow.response:
                self.establish_server_connection(flow)

    def process_request_hook(self, flow):
        # Determine .scheme, .host and .port attributes for inline scripts.
        # For absolute-form requests, they are directly given in the request.
        # For authority-form requests, we only need to determine the request scheme.
        # For relative-form requests, we need to determine host and port as
        # well.
        if self.mode == "regular":
            pass  # only absolute-form at this point, nothing to do here.
        elif self.mode == "upstream":
            if flow.request.form_in == "authority":
                flow.request.scheme = "http"  # pseudo value
        else:
            flow.request.host = self.ctx.server_address.host
            flow.request.port = self.ctx.server_address.port
            flow.request.scheme = self.server_conn.tls_established

        # TODO: Expose ChangeServer functionality to inline scripts somehow? (yield_from_callback?)
        request_reply = self.c.channel.ask("request", flow)
        if request_reply is None or request_reply == KILL:
            return False
        if isinstance(request_reply, HTTPResponse):
            flow.response = request_reply
            return

    def establish_server_connection(self, flow):

        address = tcp.Address((flow.request.host, flow.request.port))
        tls = (flow.request.scheme == "https")
        if self.mode == "regular" or self.mode == "transparent":
            # If there's an existing connection that doesn't match our expectations, kill it.
            if self.server_address != address or tls != self.server_address.ssl_established:
                yield ChangeServer(address, tls, address.host)
            # Establish connection is neccessary.
            if not self.server_conn:
                yield Connect()

            # ChangeServer is not guaranteed to work with TLS:
            # If there's not TlsLayer below which could catch the exception,
            # TLS will not be established.
            if tls and not self.server_conn.tls_established:
                raise ProtocolException("Cannot upgrade to SSL, no TLS layer on the protocol stack.")

        else:
            if tls:
                raise HttpException("Cannot change scheme in upstream proxy mode.")
            """
            # This is a very ugly (untested) workaround to solve a very ugly problem.
            # FIXME: Check if connected first.
            if self.server_conn.tls_established and not ssl:
                yield Reconnect()
            elif ssl and not hasattr(self, "connected_to") or self.connected_to != address:
                if self.server_conn.tls_established:
                    yield Reconnect()

                self.send_to_server(make_connect_request(address))
                tls_layer = TlsLayer(self, False, True)
                tls_layer._establish_tls_with_server()
            """

    def validate_request(self, request):
        if request.form_in == "absolute" and request.scheme != "http":
            self.send_resplonse(make_error_response(400, "Invalid request scheme: %s" % request.scheme))
            raise HttpException("Invalid request scheme: %s" % request.scheme)

        expected_request_forms = {
            "regular": ("absolute",), # an authority request would already be handled.
            "upstream": ("authority", "absolute"),
            "transparent": ("regular",)
        }

        allowed_request_forms = expected_request_forms[self.mode]
        if request.form_in not in allowed_request_forms:
            err_message = "Invalid HTTP request form (expected: %s, got: %s)" % (
                " or ".join(allowed_request_forms), request.form_in
            )
            self.send_to_client(make_error_response(400, err_message))
            raise HttpException(err_message)

    def authenticate(self, request):
        if self.config.authenticator:
            if self.config.authenticator.authenticate(request.headers):
                self.config.authenticator.clean(request.headers)
            else:
                self.send_to_client(make_error_response(
                    407,
                    "Proxy Authentication Required",
                    self.config.authenticator.auth_challenge_headers()
                ))
                raise InvalidCredentials("Proxy Authentication Required")

    def send_to_server(self, message):
        self.server_conn.wfile.wrie(message)

    def send_to_client(self, message):
        # FIXME
        # - possibly do some http2 stuff here
        # - fix message assembly.
        self.client_conn.wfile.write(message)
