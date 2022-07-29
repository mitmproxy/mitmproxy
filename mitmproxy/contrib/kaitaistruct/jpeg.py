# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

from . import exif
class Jpeg(KaitaiStruct):
    """JPEG File Interchange Format, or JFIF, or, more colloquially known
    as just "JPEG" or "JPG", is a popular 2D bitmap image file format,
    offering lossy compression which works reasonably well with
    photographic images.
    
    Format is organized as a container format, serving multiple
    "segments", each starting with a magic and a marker. JFIF standard
    dictates order and mandatory apperance of segments:
    
    * SOI
    * APP0 (with JFIF magic)
    * APP0 (with JFXX magic, optional)
    * everything else
    * SOS
    * JPEG-compressed stream
    * EOI
    """

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
        self._read()

    def _read(self):
        self.segments = []
        i = 0
        while not self._io.is_eof():
            self.segments.append(Jpeg.Segment(self._io, self, self._root))
            i += 1


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
            self._read()

        def _read(self):
            self.magic = self._io.read_bytes(1)
            if not self.magic == b"\xFF":
                raise kaitaistruct.ValidationNotEqualError(b"\xFF", self.magic, self._io, u"/types/segment/seq/0")
            self.marker = KaitaiStream.resolve_enum(Jpeg.Segment.MarkerEnum, self._io.read_u1())
            if  ((self.marker != Jpeg.Segment.MarkerEnum.soi) and (self.marker != Jpeg.Segment.MarkerEnum.eoi)) :
                self.length = self._io.read_u2be()

            if  ((self.marker != Jpeg.Segment.MarkerEnum.soi) and (self.marker != Jpeg.Segment.MarkerEnum.eoi)) :
                _on = self.marker
                if _on == Jpeg.Segment.MarkerEnum.app1:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                    self.data = Jpeg.SegmentApp1(_io__raw_data, self, self._root)
                elif _on == Jpeg.Segment.MarkerEnum.app0:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                    self.data = Jpeg.SegmentApp0(_io__raw_data, self, self._root)
                elif _on == Jpeg.Segment.MarkerEnum.sof0:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                    self.data = Jpeg.SegmentSof0(_io__raw_data, self, self._root)
                elif _on == Jpeg.Segment.MarkerEnum.sos:
                    self._raw_data = self._io.read_bytes((self.length - 2))
                    _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
                    self.data = Jpeg.SegmentSos(_io__raw_data, self, self._root)
                else:
                    self.data = self._io.read_bytes((self.length - 2))

            if self.marker == Jpeg.Segment.MarkerEnum.sos:
                self.image_data = self._io.read_bytes_full()



    class SegmentSos(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.num_components = self._io.read_u1()
            self.components = []
            for i in range(self.num_components):
                self.components.append(Jpeg.SegmentSos.Component(self._io, self, self._root))

            self.start_spectral_selection = self._io.read_u1()
            self.end_spectral = self._io.read_u1()
            self.appr_bit_pos = self._io.read_u1()

        class Component(KaitaiStruct):
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._read()

            def _read(self):
                self.id = KaitaiStream.resolve_enum(Jpeg.ComponentId, self._io.read_u1())
                self.huffman_table = self._io.read_u1()



    class SegmentApp1(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.magic = (self._io.read_bytes_term(0, False, True, True)).decode(u"ASCII")
            _on = self.magic
            if _on == u"Exif":
                self.body = Jpeg.ExifInJpeg(self._io, self, self._root)


    class SegmentSof0(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.bits_per_sample = self._io.read_u1()
            self.image_height = self._io.read_u2be()
            self.image_width = self._io.read_u2be()
            self.num_components = self._io.read_u1()
            self.components = []
            for i in range(self.num_components):
                self.components.append(Jpeg.SegmentSof0.Component(self._io, self, self._root))


        class Component(KaitaiStruct):
            def __init__(self, _io, _parent=None, _root=None):
                self._io = _io
                self._parent = _parent
                self._root = _root if _root else self
                self._read()

            def _read(self):
                self.id = KaitaiStream.resolve_enum(Jpeg.ComponentId, self._io.read_u1())
                self.sampling_factors = self._io.read_u1()
                self.quantization_table_id = self._io.read_u1()

            @property
            def sampling_x(self):
                if hasattr(self, '_m_sampling_x'):
                    return self._m_sampling_x

                self._m_sampling_x = ((self.sampling_factors & 240) >> 4)
                return getattr(self, '_m_sampling_x', None)

            @property
            def sampling_y(self):
                if hasattr(self, '_m_sampling_y'):
                    return self._m_sampling_y

                self._m_sampling_y = (self.sampling_factors & 15)
                return getattr(self, '_m_sampling_y', None)



    class ExifInJpeg(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.extra_zero = self._io.read_bytes(1)
            if not self.extra_zero == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.extra_zero, self._io, u"/types/exif_in_jpeg/seq/0")
            self._raw_data = self._io.read_bytes_full()
            _io__raw_data = KaitaiStream(BytesIO(self._raw_data))
            self.data = exif.Exif(_io__raw_data)


    class SegmentApp0(KaitaiStruct):

        class DensityUnit(Enum):
            no_units = 0
            pixels_per_inch = 1
            pixels_per_cm = 2
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.magic = (self._io.read_bytes(5)).decode(u"ASCII")
            self.version_major = self._io.read_u1()
            self.version_minor = self._io.read_u1()
            self.density_units = KaitaiStream.resolve_enum(Jpeg.SegmentApp0.DensityUnit, self._io.read_u1())
            self.density_x = self._io.read_u2be()
            self.density_y = self._io.read_u2be()
            self.thumbnail_x = self._io.read_u1()
            self.thumbnail_y = self._io.read_u1()
            self.thumbnail = self._io.read_bytes(((self.thumbnail_x * self.thumbnail_y) * 3))



