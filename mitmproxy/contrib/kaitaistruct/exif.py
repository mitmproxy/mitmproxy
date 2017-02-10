# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# The source was exif.ksy from here - https://github.com/kaitai-io/kaitai_struct_formats/blob/24e2d00048b8084ceec30a187a79cb87a79a48ba/image/exif.ksy

import array
import struct
import zlib
from enum import Enum

from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


from .exif_le import ExifLe
from .exif_be import ExifBe
class Exif(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.endianness = self._io.read_u2le()
        _on = self.endianness
        if _on == 18761:
            self.body = ExifLe(self._io)
        elif _on == 19789:
            self.body = ExifBe(self._io)
