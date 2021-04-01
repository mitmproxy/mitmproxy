# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO


if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))

class VlqBase128Le(KaitaiStruct):
    """A variable-length unsigned integer using base128 encoding. 1-byte groups
    consists of 1-bit flag of continuation and 7-bit value, and are ordered
    "least significant group first", i.e. in "little-endian" manner.
    
    This particular encoding is specified and used in:
    
    * DWARF debug file format, where it's dubbed "unsigned LEB128" or "ULEB128".
      http://dwarfstd.org/doc/dwarf-2.0.0.pdf - page 139
    * Google Protocol Buffers, where it's called "Base 128 Varints".
      https://developers.google.com/protocol-buffers/docs/encoding?csw=1#varints
    * Apache Lucene, where it's called "VInt"
      http://lucene.apache.org/core/3_5_0/fileformats.html#VInt
    * Apache Avro uses this as a basis for integer encoding, adding ZigZag on
      top of it for signed ints
      http://avro.apache.org/docs/current/spec.html#binary_encode_primitive
    
    More information on this encoding is available at https://en.wikipedia.org/wiki/LEB128
    
    This particular implementation supports serialized values to up 8 bytes long.
    """
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.groups = []
        while True:
            _ = self._root.Group(self._io, self, self._root)
            self.groups.append(_)
            if not (_.has_next):
                break

    class Group(KaitaiStruct):
        """One byte group, clearly divided into 7-bit "value" and 1-bit "has continuation
        in the next byte" flag.
        """
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.b = self._io.read_u1()

        @property
        def has_next(self):
            """If true, then we have more bytes to read."""
            if hasattr(self, '_m_has_next'):
                return self._m_has_next if hasattr(self, '_m_has_next') else None

            self._m_has_next = (self.b & 128) != 0
            return self._m_has_next if hasattr(self, '_m_has_next') else None

        @property
        def value(self):
            """The 7-bit (base128) numeric value of this group."""
            if hasattr(self, '_m_value'):
                return self._m_value if hasattr(self, '_m_value') else None

            self._m_value = (self.b & 127)
            return self._m_value if hasattr(self, '_m_value') else None


    @property
    def len(self):
        if hasattr(self, '_m_len'):
            return self._m_len if hasattr(self, '_m_len') else None

        self._m_len = len(self.groups)
        return self._m_len if hasattr(self, '_m_len') else None

    @property
    def value(self):
        """Resulting value as normal integer."""
        if hasattr(self, '_m_value'):
            return self._m_value if hasattr(self, '_m_value') else None

        self._m_value = (((((((self.groups[0].value + ((self.groups[1].value << 7) if self.len >= 2 else 0)) + ((self.groups[2].value << 14) if self.len >= 3 else 0)) + ((self.groups[3].value << 21) if self.len >= 4 else 0)) + ((self.groups[4].value << 28) if self.len >= 5 else 0)) + ((self.groups[5].value << 35) if self.len >= 6 else 0)) + ((self.groups[6].value << 42) if self.len >= 7 else 0)) + ((self.groups[7].value << 49) if self.len >= 8 else 0))
        return self._m_value if hasattr(self, '_m_value') else None


