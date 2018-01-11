# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import array
import struct
import zlib
from enum import Enum
from pkg_resources import parse_version

from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class Gif(KaitaiStruct):

    class BlockType(Enum):
        extension = 33
        local_image_descriptor = 44
        end_of_file = 59

    class ExtensionLabel(Enum):
        graphic_control = 249
        comment = 254
        application = 255
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.hdr = self._root.Header(self._io, self, self._root)
        self.logical_screen_descriptor = self._root.LogicalScreenDescriptorStruct(self._io, self, self._root)
        if self.logical_screen_descriptor.has_color_table:
            self._raw_global_color_table = self._io.read_bytes((self.logical_screen_descriptor.color_table_size * 3))
            io = KaitaiStream(BytesIO(self._raw_global_color_table))
            self.global_color_table = self._root.ColorTable(io, self, self._root)

        self.blocks = []
        while True:
            _ = self._root.Block(self._io, self, self._root)
            self.blocks.append(_)
            if  ((self._io.is_eof()) or (_.block_type == self._root.BlockType.end_of_file)) :
                break

    class ImageData(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.lzw_min_code_size = self._io.read_u1()
            self.subblocks = self._root.Subblocks(self._io, self, self._root)


    class ColorTableEntry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.red = self._io.read_u1()
            self.green = self._io.read_u1()
            self.blue = self._io.read_u1()


    class LogicalScreenDescriptorStruct(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.screen_width = self._io.read_u2le()
            self.screen_height = self._io.read_u2le()
            self.flags = self._io.read_u1()
            self.bg_color_index = self._io.read_u1()
            self.pixel_aspect_ratio = self._io.read_u1()

        @property
        def has_color_table(self):
            if hasattr(self, '_m_has_color_table'):
                return self._m_has_color_table if hasattr(self, '_m_has_color_table') else None

            self._m_has_color_table = (self.flags & 128) != 0
            return self._m_has_color_table if hasattr(self, '_m_has_color_table') else None

        @property
        def color_table_size(self):
            if hasattr(self, '_m_color_table_size'):
                return self._m_color_table_size if hasattr(self, '_m_color_table_size') else None

            self._m_color_table_size = (2 << (self.flags & 7))
            return self._m_color_table_size if hasattr(self, '_m_color_table_size') else None


    class LocalImageDescriptor(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.left = self._io.read_u2le()
            self.top = self._io.read_u2le()
            self.width = self._io.read_u2le()
            self.height = self._io.read_u2le()
            self.flags = self._io.read_u1()
            if self.has_color_table:
                self._raw_local_color_table = self._io.read_bytes((self.color_table_size * 3))
                io = KaitaiStream(BytesIO(self._raw_local_color_table))
                self.local_color_table = self._root.ColorTable(io, self, self._root)

            self.image_data = self._root.ImageData(self._io, self, self._root)

        @property
        def has_color_table(self):
            if hasattr(self, '_m_has_color_table'):
                return self._m_has_color_table if hasattr(self, '_m_has_color_table') else None

            self._m_has_color_table = (self.flags & 128) != 0
            return self._m_has_color_table if hasattr(self, '_m_has_color_table') else None

        @property
        def has_interlace(self):
            if hasattr(self, '_m_has_interlace'):
                return self._m_has_interlace if hasattr(self, '_m_has_interlace') else None

            self._m_has_interlace = (self.flags & 64) != 0
            return self._m_has_interlace if hasattr(self, '_m_has_interlace') else None

        @property
        def has_sorted_color_table(self):
            if hasattr(self, '_m_has_sorted_color_table'):
                return self._m_has_sorted_color_table if hasattr(self, '_m_has_sorted_color_table') else None

            self._m_has_sorted_color_table = (self.flags & 32) != 0
            return self._m_has_sorted_color_table if hasattr(self, '_m_has_sorted_color_table') else None

        @property
        def color_table_size(self):
            if hasattr(self, '_m_color_table_size'):
                return self._m_color_table_size if hasattr(self, '_m_color_table_size') else None

            self._m_color_table_size = (2 << (self.flags & 7))
            return self._m_color_table_size if hasattr(self, '_m_color_table_size') else None


    class Block(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.block_type = self._root.BlockType(self._io.read_u1())
            _on = self.block_type
            if _on == self._root.BlockType.extension:
                self.body = self._root.Extension(self._io, self, self._root)
            elif _on == self._root.BlockType.local_image_descriptor:
                self.body = self._root.LocalImageDescriptor(self._io, self, self._root)


    class ColorTable(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.entries = []
            while not self._io.is_eof():
                self.entries.append(self._root.ColorTableEntry(self._io, self, self._root))



    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.magic = self._io.ensure_fixed_contents(struct.pack('3b', 71, 73, 70))
            self.version = (self._io.read_bytes(3)).decode(u"ASCII")


    class ExtGraphicControl(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.block_size = self._io.ensure_fixed_contents(struct.pack('1b', 4))
            self.flags = self._io.read_u1()
            self.delay_time = self._io.read_u2le()
            self.transparent_idx = self._io.read_u1()
            self.terminator = self._io.ensure_fixed_contents(struct.pack('1b', 0))

        @property
        def transparent_color_flag(self):
            if hasattr(self, '_m_transparent_color_flag'):
                return self._m_transparent_color_flag if hasattr(self, '_m_transparent_color_flag') else None

            self._m_transparent_color_flag = (self.flags & 1) != 0
            return self._m_transparent_color_flag if hasattr(self, '_m_transparent_color_flag') else None

        @property
        def user_input_flag(self):
            if hasattr(self, '_m_user_input_flag'):
                return self._m_user_input_flag if hasattr(self, '_m_user_input_flag') else None

            self._m_user_input_flag = (self.flags & 2) != 0
            return self._m_user_input_flag if hasattr(self, '_m_user_input_flag') else None


    class Subblock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.num_bytes = self._io.read_u1()
            self.bytes = self._io.read_bytes(self.num_bytes)


    class ExtApplication(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.application_id = self._root.Subblock(self._io, self, self._root)
            self.subblocks = []
            while True:
                _ = self._root.Subblock(self._io, self, self._root)
                self.subblocks.append(_)
                if _.num_bytes == 0:
                    break


    class Subblocks(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.entries = []
            while True:
                _ = self._root.Subblock(self._io, self, self._root)
                self.entries.append(_)
                if _.num_bytes == 0:
                    break


    class Extension(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.label = self._root.ExtensionLabel(self._io.read_u1())
            _on = self.label
            if _on == self._root.ExtensionLabel.application:
                self.body = self._root.ExtApplication(self._io, self, self._root)
            elif _on == self._root.ExtensionLabel.comment:
                self.body = self._root.Subblocks(self._io, self, self._root)
            elif _on == self._root.ExtensionLabel.graphic_control:
                self.body = self._root.ExtGraphicControl(self._io, self, self._root)
            else:
                self.body = self._root.Subblocks(self._io, self, self._root)



