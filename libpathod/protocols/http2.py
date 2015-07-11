from netlib import tcp, http, http2, wsgi, certutils, websockets, odict
from .. import version, app, language, utils, log

class HTTP2Protocol:

    def __init__(self, pathod_handler):
        self.pathod_handler = pathod_handler
        self.wire_protocol = http2.HTTP2Protocol(
            self.pathod_handler, is_server=True, dump_frames=self.pathod_handler.http2_framedump
        )

    def make_error_response(self, reason, body):
        return language.http2.make_error_response(reason, body)

    def read_request(self):
        self.wire_protocol.perform_server_connection_preface()
        return self.wire_protocol.read_request()

    def create_response(self, code, stream_id, headers, body):
        return self.wire_protocol.create_response(code, stream_id, headers, body)
