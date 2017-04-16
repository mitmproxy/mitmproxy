# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import array
import struct
import zlib
from enum import Enum
from pkg_resources import parse_version

from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

from .exif import Exif

class Jpeg(KaitaiStruct):

    class ComponentId(Enum):
        y = 1
        cb = 2
        cr = 3
        i = 4
        q = 5
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.segments = []
        while not self._io.is_eof():
            self.segments.append(self._root.Segment(self._io, self, self._root))


    class Segment(KaitaiStruct):

        class MarkerEnum(Enum):
            tem = 1
            sof0 = 192
            sof1 = 193
            sof2 = 194
            sof3 = 195
            dht = 196
            sof5 = 197
            sof6 = 198
            sof7 = 199
            soi = 216
            eoi = 217
            sos = 218
            dqt = 219
            dnl = 220
            dri = 221
            dhp = 222
            app0 = 224
            app1 = 225
            app2 = 226
            app3 = 227
            app4 = 228
            app5 = 229
            app6 = 230
            app7 = 231
            app8 = 232
            app9 = 233
            app10 = 234
            app11 = 235
            app12 = 236
            app13 = 237
            app14 = 238
            app15 = 239
            com = 254
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.magic = self._io.ensure_fixed_contents(struct.pack('1b', -1))
            self.marker = self._root.Segment.MarkerEnum(self._io.read_u1())
            if  ((self.marker != self._root.Segment.MarkerEnum.soi) and (self.marker != self._root.Segment.MarkerEnum.eoi)) :
                self.length = self._io.read_u2be()

            if  ((self.marker != self._root.Segment.MarkerEnum.soi) and (self.marker != self._root.Segment.MarkerEnum.eoi)) :
                _on = self.marker
                if _on == self._root.Segment.MarkerEnum.sos:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    io = KaitaiStream(BytesIO(self._raw_data))
                    self.data = self._root.SegmentSos(io, self, self._root)
                elif _on == self._root.Segment.MarkerEnum.app1:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    io = KaitaiStream(BytesIO(self._raw_data))
                    self.data = self._root.SegmentApp1(io, self, self._root)
                elif _on == self._root.Segment.MarkerEnum.sof0:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    io = KaitaiStream(BytesIO(self._raw_data))
                    self.data = self._root.SegmentSof0(io, self, self._root)
                elif _on == self._root.Segment.MarkerEnum.app0:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    io = KaitaiStream(BytesIO(self._raw_data))
                    self.data = self._root.SegmentApp0(io, self, self._root)
                else:
                    self.data = self._io.read_bytes((self.length - 2))

            if self.marker == self._root.Segment.MarkerEnum.sos:
                self.image_data = self._io.read_bytes_full()



    class SegmentSos(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.num_components = self._io.read_u1()
            self.components = [None] * (self.num_components)
            for i in range(self.num_components):
                self.components[i] = self._root.SegmentSos.Component(self._io, self, self._root)

            self.start_spectral_selection = self._io.read_u1()
            self.end_spectral = self._io.read_u1()
            self.appr_bit_pos = self._io.read_u1()

        class Component(KaitaiStruct):
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self.id = self._root.ComponentId(self._io.read_u1())
                self.huffman_table = self._io.read_u1()



    class SegmentApp1(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.magic = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            _on = self.magic
            if _on == u"Exif":
                self.body = self._root.ExifInJpeg(self._io, self, self._root)


    class SegmentSof0(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.bits_per_sample = self._io.read_u1()
            self.image_height = self._io.read_u2be()
            self.image_width = self._io.read_u2be()
            self.num_components = self._io.read_u1()
            self.components = [None] * (self.num_components)
            for i in range(self.num_components):
                self.components[i] = self._root.SegmentSof0.Component(self._io, self, self._root)


        class Component(KaitaiStruct):
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self.id = self._root.ComponentId(self._io.read_u1())
                self.sampling_factors = self._io.read_u1()
                self.quantization_table_id = self._io.read_u1()

            @property
            def sampling_x(self):
                if hasattr(self, '_m_sampling_x'):
                    return self._m_sampling_x if hasattr(self, '_m_sampling_x') else None

                self._m_sampling_x = ((self.sampling_factors & 240) >> 4)
                return self._m_sampling_x if hasattr(self, '_m_sampling_x') else None

            @property
            def sampling_y(self):
                if hasattr(self, '_m_sampling_y'):
                    return self._m_sampling_y if hasattr(self, '_m_sampling_y') else None

                self._m_sampling_y = (self.sampling_factors & 15)
                return self._m_sampling_y if hasattr(self, '_m_sampling_y') else None



    class ExifInJpeg(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.extra_zero = self._io.ensure_fixed_contents(struct.pack('1b', 0))
            self._raw_data = self._io.read_bytes_full()
            io = KaitaiStream(BytesIO(self._raw_data))
            self.data = Exif(io)


    class SegmentApp0(KaitaiStruct):

        class DensityUnit(Enum):
            no_units = 0
            pixels_per_inch = 1
            pixels_per_cm = 2
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.magic = (self._io.read_bytes(5)).decode(u"ASCII")
            self.version_major = self._io.read_u1()
            self.version_minor = self._io.read_u1()
            self.density_units = self._root.SegmentApp0.DensityUnit(self._io.read_u1())
            self.density_x = self._io.read_u2be()
            self.density_y = self._io.read_u2be()
            self.thumbnail_x = self._io.read_u1()
            self.thumbnail_y = self._io.read_u1()
            self.thumbnail = self._io.read_bytes(((self.thumbnail_x * self.thumbnail_y) * 3))
