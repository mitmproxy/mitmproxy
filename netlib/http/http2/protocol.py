from __future__ import (absolute_import, print_function, division)
import itertools
import time

from hpack.hpack import Encoder, Decoder
from netlib import http, utils, odict
from netlib.http import semantics
from . import frame


class TCPHandler(object):

    def __init__(self, rfile, wfile=None):
        self.rfile = rfile
        self.wfile = wfile


class HTTP2Protocol(semantics.ProtocolMixin):

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

    def __init__(
        self,
        tcp_handler=None,
        rfile=None,
        wfile=None,
        is_server=False,
        dump_frames=False,
        encoder=None,
        decoder=None,
    ):
        self.tcp_handler = tcp_handler or TCPHandler(rfile, wfile)
        self.is_server = is_server
        self.dump_frames = dump_frames
        self.encoder = encoder or Encoder()
        self.decoder = decoder or Decoder()

        self.http2_settings = frame.HTTP2_DEFAULT_SETTINGS.copy()
        self.current_stream_id = None
        self.connection_preface_performed = False

    def read_request(
        self,
        include_body=True,
        body_size_limit=None,
        allow_empty=False,
    ):
        self.perform_connection_preface()

        timestamp_start = time.time()
        if hasattr(self.tcp_handler.rfile, "reset_timestamps"):
            self.tcp_handler.rfile.reset_timestamps()

        stream_id, headers, body = self._receive_transmission(include_body)

        if hasattr(self.tcp_handler.rfile, "first_byte_timestamp"):
            # more accurate timestamp_start
            timestamp_start = self.tcp_handler.rfile.first_byte_timestamp

        timestamp_end = time.time()

        request = http.Request(
            "relative",  # TODO: use the correct value
            headers.get_first(':method', 'GET'),
            headers.get_first(':scheme', 'https'),
            headers.get_first(':host', 'localhost'),
            443,  # TODO: parse port number from host?
            headers.get_first(':path', '/'),
            (2, 0),
            headers,
            body,
            timestamp_start,
            timestamp_end,
        )
        request.stream_id = stream_id

        return request

    def read_response(
        self,
        request_method='',
        body_size_limit=None,
        include_body=True,
    ):
        self.perform_connection_preface()

        timestamp_start = time.time()
        if hasattr(self.tcp_handler.rfile, "reset_timestamps"):
            self.tcp_handler.rfile.reset_timestamps()

        stream_id, headers, body = self._receive_transmission(include_body)

        if hasattr(self.tcp_handler.rfile, "first_byte_timestamp"):
            # more accurate timestamp_start
            timestamp_start = self.tcp_handler.rfile.first_byte_timestamp

        if include_body:
            timestamp_end = time.time()
        else:
            timestamp_end = None

        response = http.Response(
            (2, 0),
            int(headers.get_first(':status')),
            "",
            headers,
            body,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )
        response.stream_id = stream_id

        return response

    def assemble_request(self, request):
        assert isinstance(request, semantics.Request)

        authority = self.tcp_handler.sni if self.tcp_handler.sni else self.tcp_handler.address.host
        if self.tcp_handler.address.port != 443:
            authority += ":%d" % self.tcp_handler.address.port

        headers = request.headers.copy()

        if ':authority' not in headers.keys():
            headers.add(':authority', bytes(authority), prepend=True)
        if ':scheme' not in headers.keys():
            headers.add(':scheme', bytes(request.scheme), prepend=True)
        if ':path' not in headers.keys():
            headers.add(':path', bytes(request.path), prepend=True)
        if ':method' not in headers.keys():
            headers.add(':method', bytes(request.method), prepend=True)

        headers = headers.items()

        if hasattr(request, 'stream_id'):
            stream_id = request.stream_id
        else:
            stream_id = self._next_stream_id()

        return list(itertools.chain(
            self._create_headers(headers, stream_id, end_stream=(request.body is None or len(request.body) == 0)),
            self._create_body(request.body, stream_id)))

    def assemble_response(self, response):
        assert isinstance(response, semantics.Response)

        headers = response.headers.copy()

        if ':status' not in headers.keys():
            headers.add(':status', bytes(str(response.status_code)), prepend=True)

        headers = headers.items()

        if hasattr(response, 'stream_id'):
            stream_id = response.stream_id
        else:
            stream_id = self._next_stream_id()

        return list(itertools.chain(
            self._create_headers(headers, stream_id, end_stream=(response.body is None or len(response.body) == 0)),
            self._create_body(response.body, stream_id),
        ))

    def perform_connection_preface(self, force=False):
        if force or not self.connection_preface_performed:
            if self.is_server:
                self.perform_server_connection_preface(force)
            else:
                self.perform_client_connection_preface(force)

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
                assert frm.flags & frame.Frame.FLAG_ACK
                assert len(frm.settings) == 0
                break

    def _next_stream_id(self):
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

    def _apply_settings(self, settings, hide=False):
        for setting, value in settings.items():
            old_value = self.http2_settings[setting]
            if not old_value:
                old_value = '-'
            self.http2_settings[setting] = value

        frm = frame.SettingsFrame(
            state=self,
            flags=frame.Frame.FLAG_ACK)
        self.send_frame(frm, hide)

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

    def _receive_transmission(self, include_body=True):
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

        headers = odict.ODictCaseless()
        for header, value in self.decoder.decode(header_block_fragment):
            headers.add(header, value)

        return stream_id, headers, body
