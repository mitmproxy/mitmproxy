from __future__ import (absolute_import, print_function, division)

import itertools
import time

import hyperframe.frame
from hpack.hpack import Encoder, Decoder

from netlib import utils
from netlib.http import http2
import netlib.http.headers
import netlib.http.response
import netlib.http.request

from .. import language


class TCPHandler(object):

    def __init__(self, rfile, wfile=None):
        self.rfile = rfile
        self.wfile = wfile


class HTTP2StateProtocol(object):

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

    CLIENT_CONNECTION_PREFACE = b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'

    HTTP2_DEFAULT_SETTINGS = {
        hyperframe.frame.SettingsFrame.HEADER_TABLE_SIZE: 4096,
        hyperframe.frame.SettingsFrame.ENABLE_PUSH: 1,
        hyperframe.frame.SettingsFrame.MAX_CONCURRENT_STREAMS: None,
        hyperframe.frame.SettingsFrame.INITIAL_WINDOW_SIZE: 2 ** 16 - 1,
        hyperframe.frame.SettingsFrame.MAX_FRAME_SIZE: 2 ** 14,
        hyperframe.frame.SettingsFrame.MAX_HEADER_LIST_SIZE: None,
    }

    def __init__(
        self,
        tcp_handler=None,
        rfile=None,
        wfile=None,
        is_server=False,
        dump_frames=False,
        encoder=None,
        decoder=None,
        unhandled_frame_cb=None,
    ):
        self.tcp_handler = tcp_handler or TCPHandler(rfile, wfile)
        self.is_server = is_server
        self.dump_frames = dump_frames
        self.encoder = encoder or Encoder()
        self.decoder = decoder or Decoder()
        self.unhandled_frame_cb = unhandled_frame_cb

        self.http2_settings = self.HTTP2_DEFAULT_SETTINGS.copy()
        self.current_stream_id = None
        self.connection_preface_performed = False

    def read_request(
        self,
        __rfile,
        include_body=True,
        body_size_limit=None,
        allow_empty=False,
    ):
        if body_size_limit is not None:
            raise NotImplementedError()

        self.perform_connection_preface()

        timestamp_start = time.time()
        if hasattr(self.tcp_handler.rfile, "reset_timestamps"):
            self.tcp_handler.rfile.reset_timestamps()

        stream_id, headers, body = self._receive_transmission(
            include_body=include_body,
        )

        if hasattr(self.tcp_handler.rfile, "first_byte_timestamp"):
            # more accurate timestamp_start
            timestamp_start = self.tcp_handler.rfile.first_byte_timestamp

        timestamp_end = time.time()

        first_line_format, method, scheme, host, port, path = http2.parse_headers(headers)

        request = netlib.http.request.Request(
            first_line_format,
            method,
            scheme,
            host,
            port,
            path,
            b"HTTP/2.0",
            headers,
            body,
            timestamp_start,
            timestamp_end,
        )
        request.stream_id = stream_id

        return request

    def read_response(
        self,
        __rfile,
        request_method=b'',
        body_size_limit=None,
        include_body=True,
        stream_id=None,
    ):
        if body_size_limit is not None:
            raise NotImplementedError()

        self.perform_connection_preface()

        timestamp_start = time.time()
        if hasattr(self.tcp_handler.rfile, "reset_timestamps"):
            self.tcp_handler.rfile.reset_timestamps()

        stream_id, headers, body = self._receive_transmission(
            stream_id=stream_id,
            include_body=include_body,
        )

        if hasattr(self.tcp_handler.rfile, "first_byte_timestamp"):
            # more accurate timestamp_start
            timestamp_start = self.tcp_handler.rfile.first_byte_timestamp

        if include_body:
            timestamp_end = time.time()
        else:
            timestamp_end = None

        response = netlib.http.response.Response(
            b"HTTP/2.0",
            int(headers.get(':status', 502)),
            b'',
            headers,
            body,
            timestamp_start=timestamp_start,
            timestamp_end=timestamp_end,
        )
        response.stream_id = stream_id

        return response

    def assemble(self, message):
        if isinstance(message, netlib.http.request.Request):
            return self.assemble_request(message)
        elif isinstance(message, netlib.http.response.Response):
            return self.assemble_response(message)
        else:
            raise ValueError("HTTP message not supported.")

    def assemble_request(self, request):
        assert isinstance(request, netlib.http.request.Request)

        authority = self.tcp_handler.sni if self.tcp_handler.sni else self.tcp_handler.address.host
        if self.tcp_handler.address.port != 443:
            authority += ":%d" % self.tcp_handler.address.port

        headers = request.headers.copy()

        if ':authority' not in headers:
            headers.insert(0, ':authority', authority)
        headers.insert(0, ':scheme', request.scheme)
        headers.insert(0, ':path', request.path)
        headers.insert(0, ':method', request.method)

        if hasattr(request, 'stream_id'):
            stream_id = request.stream_id
        else:
            stream_id = self._next_stream_id()

        return list(itertools.chain(
            self._create_headers(headers, stream_id, end_stream=(request.body is None or len(request.body) == 0)),
            self._create_body(request.body, stream_id)))

    def assemble_response(self, response):
        assert isinstance(response, netlib.http.response.Response)

        headers = response.headers.copy()

        if ':status' not in headers:
            headers.insert(0, b':status', str(response.status_code).encode())

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

            frm = hyperframe.frame.SettingsFrame(settings={
                hyperframe.frame.SettingsFrame.ENABLE_PUSH: 0,
                hyperframe.frame.SettingsFrame.MAX_CONCURRENT_STREAMS: 1,
            })
            self.send_frame(frm, hide=True)
            self._receive_settings(hide=True)

    def perform_client_connection_preface(self, force=False):
        if force or not self.connection_preface_performed:
            self.connection_preface_performed = True

            self.tcp_handler.wfile.write(self.CLIENT_CONNECTION_PREFACE)

            self.send_frame(hyperframe.frame.SettingsFrame(), hide=True)
            self._receive_settings(hide=True)  # server announces own settings
            self._receive_settings(hide=True)  # server acks my settings

    def send_frame(self, frm, hide=False):
        raw_bytes = frm.serialize()
        self.tcp_handler.wfile.write(raw_bytes)
        self.tcp_handler.wfile.flush()
        if not hide and self.dump_frames:  # pragma no cover
            print(">> " + repr(frm))

    def read_frame(self, hide=False):
        while True:
            frm = http2.parse_frame(*http2.read_raw_frame(self.tcp_handler.rfile))
            if not hide and self.dump_frames:  # pragma no cover
                print("<< " + repr(frm))

            if isinstance(frm, hyperframe.frame.PingFrame):
                raw_bytes = hyperframe.frame.PingFrame(flags=['ACK'], payload=frm.payload).serialize()
                self.tcp_handler.wfile.write(raw_bytes)
                self.tcp_handler.wfile.flush()
                continue
            if isinstance(frm, hyperframe.frame.SettingsFrame) and 'ACK' not in frm.flags:
                self._apply_settings(frm.settings, hide)
            if isinstance(frm, hyperframe.frame.DataFrame) and frm.flow_controlled_length > 0:
                self._update_flow_control_window(frm.stream_id, frm.flow_controlled_length)
            return frm

    def check_alpn(self):
        alp = self.tcp_handler.get_alpn_proto_negotiated()
        if alp != b'h2':
            raise NotImplementedError(
                "HTTP2Protocol can not handle unknown ALPN value: %s" % alp)
        return True

    def _handle_unexpected_frame(self, frm):
        if isinstance(frm, hyperframe.frame.SettingsFrame):
            return
        if self.unhandled_frame_cb:
            self.unhandled_frame_cb(frm)

    def _receive_settings(self, hide=False):
        while True:
            frm = self.read_frame(hide)
            if isinstance(frm, hyperframe.frame.SettingsFrame):
                break
            else:
                self._handle_unexpected_frame(frm)

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

        frm = hyperframe.frame.SettingsFrame(flags=['ACK'])
        self.send_frame(frm, hide)

    def _update_flow_control_window(self, stream_id, increment):
        frm = hyperframe.frame.WindowUpdateFrame(stream_id=0, window_increment=increment)
        self.send_frame(frm)
        frm = hyperframe.frame.WindowUpdateFrame(stream_id=stream_id, window_increment=increment)
        self.send_frame(frm)

    def _create_headers(self, headers, stream_id, end_stream=True):
        def frame_cls(chunks):
            for i in chunks:
                if i == 0:
                    yield hyperframe.frame.HeadersFrame, i
                else:
                    yield hyperframe.frame.ContinuationFrame, i

        header_block_fragment = self.encoder.encode(headers.fields)

        chunk_size = self.http2_settings[hyperframe.frame.SettingsFrame.MAX_FRAME_SIZE]
        chunks = range(0, len(header_block_fragment), chunk_size)
        frms = [frm_cls(
            flags=[],
            stream_id=stream_id,
            data=header_block_fragment[i:i + chunk_size]) for frm_cls, i in frame_cls(chunks)]

        frms[-1].flags.add('END_HEADERS')
        if end_stream:
            frms[0].flags.add('END_STREAM')

        if self.dump_frames:  # pragma no cover
            for frm in frms:
                print(">> ", repr(frm))

        return [frm.serialize() for frm in frms]

    def _create_body(self, body, stream_id):
        if body is None or len(body) == 0:
            return b''

        chunk_size = self.http2_settings[hyperframe.frame.SettingsFrame.MAX_FRAME_SIZE]
        chunks = range(0, len(body), chunk_size)
        frms = [hyperframe.frame.DataFrame(
            flags=[],
            stream_id=stream_id,
            data=body[i:i + chunk_size]) for i in chunks]
        frms[-1].flags.add('END_STREAM')

        if self.dump_frames:  # pragma no cover
            for frm in frms:
                print(">> ", repr(frm))

        return [frm.serialize() for frm in frms]

    def _receive_transmission(self, stream_id=None, include_body=True):
        if not include_body:
            raise NotImplementedError()

        body_expected = True

        header_blocks = b''
        body = b''

        while True:
            frm = self.read_frame()
            if (
                (isinstance(frm, hyperframe.frame.HeadersFrame) or isinstance(frm, hyperframe.frame.ContinuationFrame)) and
                (stream_id is None or frm.stream_id == stream_id)
            ):
                stream_id = frm.stream_id
                header_blocks += frm.data
                if 'END_STREAM' in frm.flags:
                    body_expected = False
                if 'END_HEADERS' in frm.flags:
                    break
            else:
                self._handle_unexpected_frame(frm)

        while body_expected:
            frm = self.read_frame()
            if isinstance(frm, hyperframe.frame.DataFrame) and frm.stream_id == stream_id:
                body += frm.data
                if 'END_STREAM' in frm.flags:
                    break
            else:
                self._handle_unexpected_frame(frm)

        headers = netlib.http.headers.Headers(
            [[k, v] for k, v in self.decoder.decode(header_blocks, raw=True)]
        )

        return stream_id, headers, body


class HTTP2Protocol(object):

    def __init__(self, pathod_handler):
        self.pathod_handler = pathod_handler
        self.wire_protocol = HTTP2StateProtocol(
            self.pathod_handler, is_server=True, dump_frames=self.pathod_handler.http2_framedump
        )

    def make_error_response(self, reason, body):
        return language.http2.make_error_response(reason, body)

    def read_request(self, lg=None):
        self.wire_protocol.perform_server_connection_preface()
        return self.wire_protocol.read_request(self.pathod_handler.rfile)

    def assemble(self, message):
        return self.wire_protocol.assemble(message)
