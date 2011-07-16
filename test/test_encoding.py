from libmproxy import encoding
import libpry

import cStringIO
import gzip, zlib

class udecode_identity(libpry.AutoTree):
    def test_decode(self):
        assert 'string' == encoding.decode('identity', 'string')

    def test_fallthrough(self):
        assert 'string' == encoding.decode('nonexistent encoding', 'string')

class udecode_gzip(libpry.AutoTree):
    def test_simple(self):
        s = cStringIO.StringIO()
        gf = gzip.GzipFile(fileobj=s, mode='wb')
        gf.write('string')
        gf.close()
        assert 'string' == encoding.decode('gzip', s.getvalue())

class udecode_deflate(libpry.AutoTree):
    def test_simple(self):
        assert 'string' == encoding.decode('deflate', zlib.compress('string'))
        assert 'string' == encoding.decode('deflate', zlib.compress('string')[2:-4])

tests = [
    udecode_identity(),
    udecode_gzip(),
    udecode_deflate()
]
