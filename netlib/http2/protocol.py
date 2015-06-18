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
    CLIENT_CONNECTION_PREFACE =\
        '505249202a20485454502f322e300d0a0d0a534d0d0a0d0a'.decode('hex')

    ALPN_PROTO_H2 = 'h2'

    def __init__(self, tcp_handler, is_server=False, dump_frames=False):
        self.tcp_handler = tcp_handler
        self.is_server = is_server

        self.http2_settings = frame.HTTP2_DEFAULT_SETTINGS.copy()
        self.current_stream_id = None
        self.encoder = Encoder()
        self.decoder = Decoder()
        self.connection_preface_performed = False
        self.dump_frames = dump_frames

    def check_alpn(self):
        alp = self.tcp_handler.get_alpn_proto_negotiated()
        if alp != self.ALPN_PROTO_H2:
            raise NotImplementedError(
                "HTTP2Protocol can not handle unknown ALP: %s" % alp)
        return True

    def _receive_settings(self, hide=False):
        while True:
            frm = self.read_frame(hide)
            if isinstance(frm, frame.SettingsFrame):
                break

    def _read_settings_ack(self, hide=False):  # pragma no cover
        while True:
            frm = self.read_frame(hide)
            if isinstance(frm, frame.SettingsFrame):
                assert settings_ack_frame.flags & frame.Frame.FLAG_ACK
                assert len(settings_ack_frame.settings) == 0
                break

    def perform_server_connection_preface(self, force=False):
        if force or not self.connection_preface_performed:
            self.connection_preface_performed = True

            magic_length = len(self.CLIENT_CONNECTION_PREFACE)
            magic = self.tcp_handler.rfile.safe_read(magic_length)
            assert magic == self.CLIENT_CONNECTION_PREFACE

            self.send_frame(frame.SettingsFrame(state=self), hide=True)
            self._receive_settings(hide=True)

    def perform_client_connection_preface(self, force=False):
        if force or not self.connection_preface_performed:
            self.connection_preface_performed = True

            self.tcp_handler.wfile.write(self.CLIENT_CONNECTION_PREFACE)

            self.send_frame(frame.SettingsFrame(state=self), hide=True)
            self._receive_settings(hide=True)

    def next_stream_id(self):
        if self.current_stream_id is None:
            if self.is_server:
                # servers must use even stream ids
                self.current_stream_id = 2
            else:
                # clients must use odd stream ids
                self.current_stream_id = 1
        else:
            self.current_stream_id += 2
        return self.current_stream_id

    def send_frame(self, frm, hide=False):
        raw_bytes = frm.to_bytes()
        self.tcp_handler.wfile.write(raw_bytes)
        self.tcp_handler.wfile.flush()
        if not hide and self.dump_frames:  # pragma no cover
            print(frm.human_readable(">>"))

    def read_frame(self, hide=False):
        frm = frame.Frame.from_file(self.tcp_handler.rfile, self)
        if not hide and self.dump_frames:  # pragma no cover
            print(frm.human_readable("<<"))
        if isinstance(frm, frame.SettingsFrame) and not frm.flags & frame.Frame.FLAG_ACK:
            self._apply_settings(frm.settings, hide)

        return frm

    def _apply_settings(self, settings, hide=False):
        for setting, value in settings.items():
            old_value = self.http2_settings[setting]
            if not old_value:
                old_value = '-'
            self.http2_settings[setting] = value

        self.send_frame(
            frame.SettingsFrame(
                state=self,
                flags=frame.Frame.FLAG_ACK),
                hide)

        # be liberal in what we expect from the other end
        # to be more strict use: self._read_settings_ack(hide)

    def _create_headers(self, headers, stream_id, end_stream=True):
        # TODO: implement max frame size checks and sending in chunks

        flags = frame.Frame.FLAG_END_HEADERS
        if end_stream:
            flags |= frame.Frame.FLAG_END_STREAM

        header_block_fragment = self.encoder.encode(headers)

        frm = frame.HeadersFrame(
            state=self,
            flags=flags,
            stream_id=stream_id,
            header_block_fragment=header_block_fragment)

        if self.dump_frames:  # pragma no cover
            print(frm.human_readable(">>"))

        return [frm.to_bytes()]

    def _create_body(self, body, stream_id):
        if body is None or len(body) == 0:
            return b''

        # TODO: implement max frame size checks and sending in chunks
        # TODO: implement flow-control window

        frm = frame.DataFrame(
            state=self,
            flags=frame.Frame.FLAG_END_STREAM,
            stream_id=stream_id,
            payload=body)

        if self.dump_frames:  # pragma no cover
            print(frm.human_readable(">>"))

        return [frm.to_bytes()]


    def create_request(self, method, path, headers=None, body=None):
        if headers is None:
            headers = []

        authority = self.tcp_handler.sni if self.tcp_handler.sni else self.tcp_handler.address.host
        if self.tcp_handler.address.port != 443:
            authority += ":%d" % self.tcp_handler.address.port

        headers = [
            (b':method', bytes(method)),
            (b':path', bytes(path)),
            (b':scheme', b'https'),
            (b':authority', authority),
        ] + headers

        stream_id = self.next_stream_id()

        return list(itertools.chain(
            self._create_headers(headers, stream_id, end_stream=(body is None)),
            self._create_body(body, stream_id)))

    def read_response(self):
        stream_id, headers, body = self._receive_transmission()
        return headers[':status'], headers, body

    def read_request(self):
        return self._receive_transmission()

    def _receive_transmission(self):
        body_expected = True

        stream_id = 0
        header_block_fragment = b''
        body = b''

        while True:
            frm = self.read_frame()
            if isinstance(frm, frame.HeadersFrame)\
                    or isinstance(frm, frame.ContinuationFrame):
                stream_id = frm.stream_id
                header_block_fragment += frm.header_block_fragment
                if frm.flags & frame.Frame.FLAG_END_STREAM:
                    body_expected = False
                if frm.flags & frame.Frame.FLAG_END_HEADERS:
                    break

        while body_expected:
            frm = self.read_frame()
            if isinstance(frm, frame.DataFrame):
                body += frm.payload
                if frm.flags & frame.Frame.FLAG_END_STREAM:
                    break
            # TODO: implement window update & flow

        headers = {}
        for header, value in self.decoder.decode(header_block_fragment):
            headers[header] = value

        return stream_id, headers, body

    def create_response(self, code, stream_id=None, headers=None, body=None):
        if headers is None:
            headers = []

        headers = [(b':status', bytes(str(code)))] + headers

        if not stream_id:
            stream_id = self.next_stream_id()

        return list(itertools.chain(
            self._create_headers(headers, stream_id, end_stream=(body is None)),
            self._create_body(body, stream_id),
        ))
