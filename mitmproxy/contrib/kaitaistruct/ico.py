# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO
import struct


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class Ico(KaitaiStruct):
    """Microsoft Windows uses specific file format to store applications
    icons - ICO. This is a container that contains one or more image
    files (effectively, DIB parts of BMP files or full PNG files are
    contained inside).
    
    .. seealso::
       Source - https://msdn.microsoft.com/en-us/library/ms997538.aspx
    """
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.magic = self._io.ensure_fixed_contents(struct.pack('4b', 0, 0, 1, 0))
        self.num_images = self._io.read_u2le()
        self.images = [None] * (self.num_images)
        for i in range(self.num_images):
            self.images[i] = self._root.IconDirEntry(self._io, self, self._root)


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
            self.reserved = self._io.ensure_fixed_contents(struct.pack('1b', 0))
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
                return self._m_img if hasattr(self, '_m_img') else None

            _pos = self._io.pos()
            self._io.seek(self.ofs_img)
            self._m_img = self._io.read_bytes(self.len_img)
            self._io.seek(_pos)
            return self._m_img if hasattr(self, '_m_img') else None

        @property
        def png_header(self):
            """Pre-reads first 8 bytes of the image to determine if it's an
            embedded PNG file.
            """
            if hasattr(self, '_m_png_header'):
                return self._m_png_header if hasattr(self, '_m_png_header') else None

            _pos = self._io.pos()
            self._io.seek(self.ofs_img)
            self._m_png_header = self._io.read_bytes(8)
            self._io.seek(_pos)
            return self._m_png_header if hasattr(self, '_m_png_header') else None

        @property
        def is_png(self):
            """True if this image is in PNG format."""
            if hasattr(self, '_m_is_png'):
                return self._m_is_png if hasattr(self, '_m_is_png') else None

            self._m_is_png = self.png_header == struct.pack('8b', -119, 80, 78, 71, 13, 10, 26, 10)
            return self._m_is_png if hasattr(self, '_m_is_png') else None



