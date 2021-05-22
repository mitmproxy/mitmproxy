# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import array
import struct
import zlib
from enum import Enum
from pkg_resources import parse_version

from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class Png(KaitaiStruct):

    class ColorType(Enum):
        greyscale = 0
        truecolor = 2
        indexed = 3
        greyscale_alpha = 4
        truecolor_alpha = 6

    class PhysUnit(Enum):
        unknown = 0
        meter = 1
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.magic = self._io.ensure_fixed_contents(struct.pack('8b', -119, 80, 78, 71, 13, 10, 26, 10))
        self.ihdr_len = self._io.ensure_fixed_contents(struct.pack('4b', 0, 0, 0, 13))
        self.ihdr_type = self._io.ensure_fixed_contents(struct.pack('4b', 73, 72, 68, 82))
        self.ihdr = self._root.IhdrChunk(self._io, self, self._root)
        self.ihdr_crc = self._io.read_bytes(4)
        self.chunks = []
        while True:
            _ = self._root.Chunk(self._io, self, self._root)
            self.chunks.append(_)
            if  ((_.type == u"IEND") or (self._io.is_eof())) :
                break

    class Rgb(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.r = self._io.read_u1()
            self.g = self._io.read_u1()
            self.b = self._io.read_u1()


    class Chunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.len = self._io.read_u4be()
            self.type = (self._io.read_bytes(4)).decode(u"UTF-8")
            _on = self.type
            if _on == u"iTXt":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.InternationalTextChunk(io, self, self._root)
            elif _on == u"gAMA":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.GamaChunk(io, self, self._root)
            elif _on == u"tIME":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.TimeChunk(io, self, self._root)
            elif _on == u"PLTE":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.PlteChunk(io, self, self._root)
            elif _on == u"bKGD":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.BkgdChunk(io, self, self._root)
            elif _on == u"pHYs":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.PhysChunk(io, self, self._root)
            elif _on == u"tEXt":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.TextChunk(io, self, self._root)
            elif _on == u"cHRM":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.ChrmChunk(io, self, self._root)
            elif _on == u"sRGB":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.SrgbChunk(io, self, self._root)
            elif _on == u"zTXt":
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.CompressedTextChunk(io, self, self._root)
            else:
                self.body = self._io.read_bytes(self.len)
            self.crc = self._io.read_bytes(4)


    class BkgdIndexed(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.palette_index = self._io.read_u1()


    class Point(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.x_int = self._io.read_u4be()
            self.y_int = self._io.read_u4be()

        @property
        def x(self):
            if hasattr(self, '_m_x'):
                return self._m_x if hasattr(self, '_m_x') else None

            self._m_x = (self.x_int / 100000.0)
            return self._m_x if hasattr(self, '_m_x') else None

        @property
        def y(self):
            if hasattr(self, '_m_y'):
                return self._m_y if hasattr(self, '_m_y') else None

            self._m_y = (self.y_int / 100000.0)
            return self._m_y if hasattr(self, '_m_y') else None


    class BkgdGreyscale(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.value = self._io.read_u2be()


    class ChrmChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.white_point = self._root.Point(self._io, self, self._root)
            self.red = self._root.Point(self._io, self, self._root)
            self.green = self._root.Point(self._io, self, self._root)
            self.blue = self._root.Point(self._io, self, self._root)


    class IhdrChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.width = self._io.read_u4be()
            self.height = self._io.read_u4be()
            self.bit_depth = self._io.read_u1()
            self.color_type = self._root.ColorType(self._io.read_u1())
            self.compression_method = self._io.read_u1()
            self.filter_method = self._io.read_u1()
            self.interlace_method = self._io.read_u1()


    class PlteChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.entries = []
            while not self._io.is_eof():
                self.entries.append(self._root.Rgb(self._io, self, self._root))



    class SrgbChunk(KaitaiStruct):

        class Intent(Enum):
            perceptual = 0
            relative_colorimetric = 1
            saturation = 2
            absolute_colorimetric = 3
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.render_intent = self._root.SrgbChunk.Intent(self._io.read_u1())


    class CompressedTextChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self.compression_method = self._io.read_u1()
            self._raw_text_datastream = self._io.read_bytes_full()
            self.text_datastream = zlib.decompress(self._raw_text_datastream)


    class BkgdTruecolor(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.red = self._io.read_u2be()
            self.green = self._io.read_u2be()
            self.blue = self._io.read_u2be()


    class GamaChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.gamma_int = self._io.read_u4be()

        @property
        def gamma_ratio(self):
            if hasattr(self, '_m_gamma_ratio'):
                return self._m_gamma_ratio if hasattr(self, '_m_gamma_ratio') else None

            self._m_gamma_ratio = (100000.0 / self.gamma_int)
            return self._m_gamma_ratio if hasattr(self, '_m_gamma_ratio') else None


    class BkgdChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            _on = self._root.ihdr.color_type
            if _on == self._root.ColorType.greyscale_alpha:
                self.bkgd = self._root.BkgdGreyscale(self._io, self, self._root)
            elif _on == self._root.ColorType.indexed:
                self.bkgd = self._root.BkgdIndexed(self._io, self, self._root)
            elif _on == self._root.ColorType.greyscale:
                self.bkgd = self._root.BkgdGreyscale(self._io, self, self._root)
            elif _on == self._root.ColorType.truecolor_alpha:
                self.bkgd = self._root.BkgdTruecolor(self._io, self, self._root)
            elif _on == self._root.ColorType.truecolor:
                self.bkgd = self._root.BkgdTruecolor(self._io, self, self._root)


    class PhysChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.pixels_per_unit_x = self._io.read_u4be()
            self.pixels_per_unit_y = self._io.read_u4be()
            self.unit = self._root.PhysUnit(self._io.read_u1())


    class InternationalTextChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self.compression_flag = self._io.read_u1()
            self.compression_method = self._io.read_u1()
            self.language_tag = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            self.translated_keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"UTF-8")
            self.text = (self._io.read_bytes_full()).decode(u"UTF-8")


    class TextChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.keyword = (self._io.read_bytes_term(0, False, True, True)).decode(u"iso8859-1")
            self.text = (self._io.read_bytes_full()).decode(u"iso8859-1")


    class TimeChunk(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.year = self._io.read_u2be()
            self.month = self._io.read_u1()
            self.day = self._io.read_u1()
            self.hour = self._io.read_u1()
            self.minute = self._io.read_u1()
            self.second = self._io.read_u1()



