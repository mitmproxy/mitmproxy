# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import array
import struct
import zlib
from enum import Enum
from pkg_resources import parse_version

from kaitaistruct import __version__ as ks_version, KaitaiStruct, KaitaiStream, BytesIO

if parse_version(ks_version) < parse_version('0.7'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.7 or later is required, but you have %s" % (ks_version))


class TlsClientHello(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self.version = self._root.Version(self._io, self, self._root)
        self.random = self._root.Random(self._io, self, self._root)
        self.session_id = self._root.SessionId(self._io, self, self._root)
        self.cipher_suites = self._root.CipherSuites(self._io, self, self._root)
        self.compression_methods = self._root.CompressionMethods(self._io, self, self._root)
        if self._io.is_eof() == True:
            self.extensions = [None] * (0)
            for i in range(0):
                self.extensions[i] = self._io.read_bytes(0)

        if self._io.is_eof() == False:
            self.extensions = self._root.Extensions(self._io, self, self._root)

    class ServerName(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.name_type = self._io.read_u1()
            self.length = self._io.read_u2be()
            self.host_name = self._io.read_bytes(self.length)

    class Random(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.gmt_unix_time = self._io.read_u4be()
            self.random = self._io.read_bytes(28)

    class SessionId(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.len = self._io.read_u1()
            self.sid = self._io.read_bytes(self.len)

    class Sni(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.list_length = self._io.read_u2be()
            self.server_names = []
            while not self._io.is_eof():
                self.server_names.append(self._root.ServerName(self._io, self, self._root))

    class CipherSuites(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.len = self._io.read_u2be()
            self.cipher_suites = [None] * (self.len // 2)
            for i in range(self.len // 2):
                self.cipher_suites[i] = self._io.read_u2be()

    class CompressionMethods(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.len = self._io.read_u1()
            self.compression_methods = self._io.read_bytes(self.len)

    class Alpn(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.ext_len = self._io.read_u2be()
            self.alpn_protocols = []
            while not self._io.is_eof():
                self.alpn_protocols.append(self._root.Protocol(self._io, self, self._root))

    class Extensions(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.len = self._io.read_u2be()
            self.extensions = []
            while not self._io.is_eof():
                self.extensions.append(self._root.Extension(self._io, self, self._root))

    class Version(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.major = self._io.read_u1()
            self.minor = self._io.read_u1()

    class Protocol(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.strlen = self._io.read_u1()
            self.name = self._io.read_bytes(self.strlen)

    class Extension(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self.type = self._io.read_u2be()
            self.len = self._io.read_u2be()
            _on = self.type
            if _on == 0:
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.Sni(io, self, self._root)
            elif _on == 16:
                self._raw_body = self._io.read_bytes(self.len)
                io = KaitaiStream(BytesIO(self._raw_body))
                self.body = self._root.Alpn(io, self, self._root)
            else:
                self.body = self._io.read_bytes(self.len)
