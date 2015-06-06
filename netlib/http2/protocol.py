from __future__ import (absolute_import, print_function, division)
import itertools

from hpack.hpack import Encoder, Decoder
from .. import utils
from . import frame


class HTTP2Protocol(object):

    ERROR_CODES = utils.BiDi(
        NO_ERROR=0x0,
        PROTOCOL_ERROR=0x1,
        INTERNAL_ERROR=0x2,
        FLOW_CONTROL_ERROR=0x3,
        SETTINGS_TIMEOUT=0x4,
        STREAM_CLOSED=0x5,
        FRAME_SIZE_ERROR=0x6,
        REFUSED_STREAM=0x7,
        CANCEL=0x8,
        COMPRESSION_ERROR=0x9,
        CONNECT_ERROR=0xa,
        ENHANCE_YOUR_CALM=0xb,
        INADEQUATE_SECURITY=0xc,
        HTTP_1_1_REQUIRED=0xd
    )

    # "PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
    CLIENT_CONNECTION_PREFACE = '505249202a20485454502f322e300d0a0d0a534d0d0a0d0a'

    ALPN_PROTO_H2 = 'h2'

    def __init__(self, tcp_client):
        self.tcp_client = tcp_client

        self.http2_settings = frame.HTTP2_DEFAULT_SETTINGS.copy()
        self.current_stream_id = None
        self.encoder = Encoder()
        self.decoder = Decoder()

    def check_alpn(self):
        alp = self.tcp_client.get_alpn_proto_negotiated()
        if alp != self.ALPN_PROTO_H2:
            raise NotImplementedError(
                "HTTP2Protocol can not handle unknown ALP: %s" % alp)
        return True

    def perform_connection_preface(self):
        self.tcp_client.wfile.write(
            bytes(self.CLIENT_CONNECTION_PREFACE.decode('hex')))
        self.send_frame(frame.SettingsFrame(state=self))

        # read server settings frame
        frm = frame.Frame.from_file(self.tcp_client.rfile, self)
        assert isinstance(frm, frame.SettingsFrame)
        self._apply_settings(frm.settings)

        # read setting ACK frame
        settings_ack_frame = self.read_frame()
        assert isinstance(settings_ack_frame, frame.SettingsFrame)
        assert settings_ack_frame.flags & frame.Frame.FLAG_ACK
        assert len(settings_ack_frame.settings) == 0


    def next_stream_id(self):
        if self.current_stream_id is None:
            self.current_stream_id = 1
        else:
            self.current_stream_id += 2
        return self.current_stream_id

    def send_frame(self, frame):
        raw_bytes = frame.to_bytes()
        self.tcp_client.wfile.write(raw_bytes)
        self.tcp_client.wfile.flush()

    def read_frame(self):
        frm = frame.Frame.from_file(self.tcp_client.rfile, self)
        if isinstance(frm, frame.SettingsFrame):
            self._apply_settings(frm.settings)

        return frm

    def _apply_settings(self, settings):
        for setting, value in settings.items():
            old_value = self.http2_settings[setting]
            if not old_value:
                old_value = '-'

            self.http2_settings[setting] = value

        self.send_frame(frame.SettingsFrame(state=self, flags=frame.Frame.FLAG_ACK))

    def _create_headers(self, headers, stream_id, end_stream=True):
        # TODO: implement max frame size checks and sending in chunks

        flags = frame.Frame.FLAG_END_HEADERS
        if end_stream:
            flags |= frame.Frame.FLAG_END_STREAM

        header_block_fragment = self.encoder.encode(headers)

        bytes = frame.HeadersFrame(
            state=self,
            flags=flags,
            stream_id=stream_id,
            header_block_fragment=header_block_fragment).to_bytes()
        return [bytes]

    def _create_body(self, body, stream_id):
        if body is None or len(body) == 0:
            return b''

        # TODO: implement max frame size checks and sending in chunks
        # TODO: implement flow-control window

        bytes = frame.DataFrame(
            state=self,
            flags=frame.Frame.FLAG_END_STREAM,
            stream_id=stream_id,
            payload=body).to_bytes()
        return [bytes]

    def create_request(self, method, path, headers=None, body=None):
        if headers is None:
            headers = []

        headers = [
            (b':method', bytes(method)),
            (b':path', bytes(path)),
            (b':scheme', b'https')] + headers

        stream_id = self.next_stream_id()

        return list(itertools.chain(
            self._create_headers(headers, stream_id, end_stream=(body is None)),
            self._create_body(body, stream_id)))

    def read_response(self):
        header_block_fragment = b''
        body = b''

        while True:
            frm = self.read_frame()
            if isinstance(frm, frame.HeadersFrame):
                header_block_fragment += frm.header_block_fragment
                if frm.flags | frame.Frame.FLAG_END_HEADERS:
                    break

        while True:
            frm = self.read_frame()
            if isinstance(frm, frame.DataFrame):
                body += frm.payload
                if frm.flags | frame.Frame.FLAG_END_STREAM:
                    break

        headers = {}
        for header, value in self.decoder.decode(header_block_fragment):
            headers[header] = value

        return headers[':status'], headers, body
