# type: ignore

# -*- coding: utf-8 -*-
"""
wsproto/extensions
~~~~~~~~~~~~~~

WebSocket extensions.
"""

import zlib

from .frame_protocol import CloseReason, Opcode, RsvBits


class Extension(object):
    name = None

    def enabled(self):
        return False

    def offer(self, connection):
        pass

    def accept(self, connection, offer):
        pass

    def finalize(self, connection, offer):
        pass

    def frame_inbound_header(self, proto, opcode, rsv, payload_length):
        return RsvBits(False, False, False)

    def frame_inbound_payload_data(self, proto, data):
        return data

    def frame_inbound_complete(self, proto, fin):
        pass

    def frame_outbound(self, proto, opcode, rsv, data, fin):
        return (rsv, data)


class PerMessageDeflate(Extension):
    name = 'permessage-deflate'

    DEFAULT_CLIENT_MAX_WINDOW_BITS = 15
    DEFAULT_SERVER_MAX_WINDOW_BITS = 15

    def __init__(self, client_no_context_takeover=False,
                 client_max_window_bits=None, server_no_context_takeover=False,
                 server_max_window_bits=None):
        self.client_no_context_takeover = client_no_context_takeover
        if client_max_window_bits is None:
            client_max_window_bits = self.DEFAULT_CLIENT_MAX_WINDOW_BITS
        self.client_max_window_bits = client_max_window_bits
        self.server_no_context_takeover = server_no_context_takeover
        if server_max_window_bits is None:
            server_max_window_bits = self.DEFAULT_SERVER_MAX_WINDOW_BITS
        self.server_max_window_bits = server_max_window_bits

        self._compressor = None
        self._decompressor = None
        # This refers to the current frame
        self._inbound_is_compressible = None
        # This refers to the ongoing message (which might span multiple
        # frames). Only the first frame in a fragmented message is flagged for
        # compression, so this carries that bit forward.
        self._inbound_compressed = None

        self._enabled = False

    def _compressible_opcode(self, opcode):
        return opcode in (Opcode.TEXT, Opcode.BINARY, Opcode.CONTINUATION)

    def enabled(self):
        return self._enabled

    def offer(self, connection):
        parameters = [
            'client_max_window_bits=%d' % self.client_max_window_bits,
            'server_max_window_bits=%d' % self.server_max_window_bits,
            ]

        if self.client_no_context_takeover:
            parameters.append('client_no_context_takeover')
        if self.server_no_context_takeover:
            parameters.append('server_no_context_takeover')

        return '; '.join(parameters)

    def finalize(self, connection, offer):
        bits = [b.strip() for b in offer.split(';')]
        for bit in bits[1:]:
            if bit.startswith('client_no_context_takeover'):
                self.client_no_context_takeover = True
            elif bit.startswith('server_no_context_takeover'):
                self.server_no_context_takeover = True
            elif bit.startswith('client_max_window_bits'):
                self.client_max_window_bits = int(bit.split('=', 1)[1].strip())
            elif bit.startswith('server_max_window_bits'):
                self.server_max_window_bits = int(bit.split('=', 1)[1].strip())

        self._enabled = True

    def _parse_params(self, params):
        client_max_window_bits = None
        server_max_window_bits = None

        bits = [b.strip() for b in params.split(';')]
        for bit in bits[1:]:
            if bit.startswith('client_no_context_takeover'):
                self.client_no_context_takeover = True
            elif bit.startswith('server_no_context_takeover'):
                self.server_no_context_takeover = True
            elif bit.startswith('client_max_window_bits'):
                if '=' in bit:
                    client_max_window_bits = int(bit.split('=', 1)[1].strip())
                else:
                    client_max_window_bits = self.client_max_window_bits
            elif bit.startswith('server_max_window_bits'):
                if '=' in bit:
                    server_max_window_bits = int(bit.split('=', 1)[1].strip())
                else:
                    server_max_window_bits = self.server_max_window_bits

        return client_max_window_bits, server_max_window_bits

    def accept(self, connection, offer):
        client_max_window_bits, server_max_window_bits = \
            self._parse_params(offer)

        self._enabled = True

        parameters = []

        if self.client_no_context_takeover:
            parameters.append('client_no_context_takeover')
        if client_max_window_bits is not None:
            parameters.append('client_max_window_bits=%d' %
                              client_max_window_bits)
            self.client_max_window_bits = client_max_window_bits
        if self.server_no_context_takeover:
            parameters.append('server_no_context_takeover')
        if server_max_window_bits is not None:
            parameters.append('server_max_window_bits=%d' %
                              server_max_window_bits)
            self.server_max_window_bits = server_max_window_bits

        return '; '.join(parameters)

    def frame_inbound_header(self, proto, opcode, rsv, payload_length):
        if rsv.rsv1 and opcode.iscontrol():
            return CloseReason.PROTOCOL_ERROR
        elif rsv.rsv1 and opcode is Opcode.CONTINUATION:
            return CloseReason.PROTOCOL_ERROR

        self._inbound_is_compressible = self._compressible_opcode(opcode)

        if self._inbound_compressed is None:
            self._inbound_compressed = rsv.rsv1
            if self._inbound_compressed:
                assert self._inbound_is_compressible
                if proto.client:
                    bits = self.server_max_window_bits
                else:
                    bits = self.client_max_window_bits
                if self._decompressor is None:
                    self._decompressor = zlib.decompressobj(-int(bits))

        return RsvBits(True, False, False)

    def frame_inbound_payload_data(self, proto, data):
        if not self._inbound_compressed or not self._inbound_is_compressible:
            return data

        try:
            return self._decompressor.decompress(bytes(data))
        except zlib.error:
            return CloseReason.INVALID_FRAME_PAYLOAD_DATA

    def frame_inbound_complete(self, proto, fin):
        if not fin:
            return
        elif not self._inbound_is_compressible:
            return
        elif not self._inbound_compressed:
            return

        try:
            data = self._decompressor.decompress(b'\x00\x00\xff\xff')
            data += self._decompressor.flush()
        except zlib.error:
            return CloseReason.INVALID_FRAME_PAYLOAD_DATA

        if proto.client:
            no_context_takeover = self.server_no_context_takeover
        else:
            no_context_takeover = self.client_no_context_takeover

        if no_context_takeover:
            self._decompressor = None

        self._inbound_compressed = None

        return data

    def frame_outbound(self, proto, opcode, rsv, data, fin):
        if not self._compressible_opcode(opcode):
            return (rsv, data)

        if opcode is not Opcode.CONTINUATION:
            rsv = RsvBits(True, *rsv[1:])

        if self._compressor is None:
            assert opcode is not Opcode.CONTINUATION
            if proto.client:
                bits = self.client_max_window_bits
            else:
                bits = self.server_max_window_bits
            self._compressor = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION,
                                                zlib.DEFLATED, -int(bits))

        data = self._compressor.compress(bytes(data))

        if fin:
            data += self._compressor.flush(zlib.Z_SYNC_FLUSH)
            data = data[:-4]

            if proto.client:
                no_context_takeover = self.client_no_context_takeover
            else:
                no_context_takeover = self.server_no_context_takeover

            if no_context_takeover:
                self._compressor = None

        return (rsv, data)

    def __repr__(self):
        descr = ['client_max_window_bits=%d' % self.client_max_window_bits]
        if self.client_no_context_takeover:
            descr.append('client_no_context_takeover')
        descr.append('server_max_window_bits=%d' % self.server_max_window_bits)
        if self.server_no_context_takeover:
            descr.append('server_no_context_takeover')

        descr = '; '.join(descr)

        return '<%s %s>' % (self.__class__.__name__, descr)


#: SUPPORTED_EXTENSIONS maps all supported extension names to their class.
#: This can be used to iterate all supported extensions of wsproto, instantiate
#: new extensions based on their name, or check if a given extension is
#: supported or not.
SUPPORTED_EXTENSIONS = {
    PerMessageDeflate.name: PerMessageDeflate
}
