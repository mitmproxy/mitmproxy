# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class DtlsClientHello(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.version = DtlsClientHello.Version(self._io, self, self._root)
        self.random = DtlsClientHello.Random(self._io, self, self._root)
        self.session_id = DtlsClientHello.SessionId(self._io, self, self._root)
        self.cookie = DtlsClientHello.Cookie(self._io, self, self._root)
        self.cipher_suites = DtlsClientHello.CipherSuites(self._io, self, self._root)
        self.compression_methods = DtlsClientHello.CompressionMethods(self._io, self, self._root)
        if self._io.is_eof() == False:
            self.extensions = DtlsClientHello.Extensions(self._io, self, self._root)


    class ServerName(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.name_type = self._io.read_u1()
            self.length = self._io.read_u2be()
            self.host_name = self._io.read_bytes(self.length)


    class Random(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.gmt_unix_time = self._io.read_u4be()
            self.random = self._io.read_bytes(28)


    class SessionId(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u1()
            self.sid = self._io.read_bytes(self.len)


    class Sni(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.list_length = self._io.read_u2be()
            self.server_names = []
            i = 0
            while not self._io.is_eof():
                self.server_names.append(DtlsClientHello.ServerName(self._io, self, self._root))
                i += 1



    class CipherSuites(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u2be()
            self.cipher_suites = []
            for i in range(self.len // 2):
                self.cipher_suites.append(self._io.read_u2be())



    class CompressionMethods(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u1()
            self.compression_methods = self._io.read_bytes(self.len)


    class Alpn(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.ext_len = self._io.read_u2be()
            self.alpn_protocols = []
            i = 0
            while not self._io.is_eof():
                self.alpn_protocols.append(DtlsClientHello.Protocol(self._io, self, self._root))
                i += 1



    class Extensions(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u2be()
            self.extensions = []
            i = 0
            while not self._io.is_eof():
                self.extensions.append(DtlsClientHello.Extension(self._io, self, self._root))
                i += 1



    class Version(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.major = self._io.read_u1()
            self.minor = self._io.read_u1()


    class Cookie(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.len = self._io.read_u1()
            self.cookie = self._io.read_bytes(self.len)


    class Protocol(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.strlen = self._io.read_u1()
            self.name = self._io.read_bytes(self.strlen)


    class Extension(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.type = self._io.read_u2be()
            self.len = self._io.read_u2be()
            _on = self.type
            if _on == 0:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = DtlsClientHello.Sni(_io__raw_body, self, self._root)
            elif _on == 16:
                self._raw_body = self._io.read_bytes(self.len)
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = DtlsClientHello.Alpn(_io__raw_body, self, self._root)
            else:
                self.body = self._io.read_bytes(self.len)



