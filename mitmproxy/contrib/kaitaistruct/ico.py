# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Ico(KaitaiStruct):
    """Microsoft Windows uses specific file format to store applications
    icons - ICO. This is a container that contains one or more image
    files (effectively, DIB parts of BMP files or full PNG files are
    contained inside).
    
    .. seealso::
       Source - https://docs.microsoft.com/en-us/previous-versions/ms997538(v=msdn.10)
    """
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.magic = self._io.read_bytes(4)
        if not self.magic == b"\x00\x00\x01\x00":
            raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x01\x00", self.magic, self._io, u"/seq/0")
        self.num_images = self._io.read_u2le()
        self.images = []
        for i in range(self.num_images):
            self.images.append(Ico.IconDirEntry(self._io, self, self._root))


    class IconDirEntry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.width = self._io.read_u1()
            self.height = self._io.read_u1()
            self.num_colors = self._io.read_u1()
            self.reserved = self._io.read_bytes(1)
            if not self.reserved == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.reserved, self._io, u"/types/icon_dir_entry/seq/3")
            self.num_planes = self._io.read_u2le()
            self.bpp = self._io.read_u2le()
            self.len_img = self._io.read_u4le()
            self.ofs_img = self._io.read_u4le()

        @property
        def img(self):
            """Raw image data. Use `is_png` to determine whether this is an
            embedded PNG file (true) or a DIB bitmap (false) and call a
            relevant parser, if needed to parse image data further.
            """
            if hasattr(self, '_m_img'):
                return self._m_img

            _pos = self._io.pos()
            self._io.seek(self.ofs_img)
            self._m_img = self._io.read_bytes(self.len_img)
            self._io.seek(_pos)
            return getattr(self, '_m_img', None)

        @property
        def png_header(self):
            """Pre-reads first 8 bytes of the image to determine if it's an
            embedded PNG file.
            """
            if hasattr(self, '_m_png_header'):
                return self._m_png_header

            _pos = self._io.pos()
            self._io.seek(self.ofs_img)
            self._m_png_header = self._io.read_bytes(8)
            self._io.seek(_pos)
            return getattr(self, '_m_png_header', None)

        @property
        def is_png(self):
            """True if this image is in PNG format."""
            if hasattr(self, '_m_is_png'):
                return self._m_is_png

            self._m_is_png = self.png_header == b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"
            return getattr(self, '_m_is_png', None)



