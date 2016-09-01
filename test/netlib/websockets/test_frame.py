import os
import codecs
import pytest

from netlib import websockets
from netlib import tutils


class TestFrameHeader(object):

    @pytest.mark.parametrize("input,expected", [
        (0, '0100'),
        (125, '017D'),
        (126, '017E007E'),
        (127, '017E007F'),
        (142, '017E008E'),
        (65534, '017EFFFE'),
        (65535, '017EFFFF'),
        (65536, '017F0000000000010000'),
        (8589934591, '017F00000001FFFFFFFF'),
        (2 ** 64 - 1, '017FFFFFFFFFFFFFFFFF'),
    ])
    def test_serialization_length(self, input, expected):
        h = websockets.FrameHeader(
            opcode=websockets.OPCODE.TEXT,
            payload_length=input,
        )
        assert bytes(h) == codecs.decode(expected, 'hex')

    def test_serialization_too_large(self):
        h = websockets.FrameHeader(
            payload_length=2 ** 64 + 1,
        )
        with pytest.raises(ValueError):
            bytes(h)

    @pytest.mark.parametrize("input,expected", [
        ('0100', 0),
        ('017D', 125),
        ('017E007E', 126),
        ('017E007F', 127),
        ('017E008E', 142),
        ('017EFFFE', 65534),
        ('017EFFFF', 65535),
        ('017F0000000000010000', 65536),
        ('017F00000001FFFFFFFF', 8589934591),
        ('017FFFFFFFFFFFFFFFFF', 2 ** 64 - 1),
    ])
    def test_deserialization_length(self, input, expected):
        h = websockets.FrameHeader.from_file(tutils.treader(codecs.decode(input, 'hex')))
        assert h.payload_length == expected

    @pytest.mark.parametrize("input,expected", [
        ('0100', (False, None)),
        ('018000000000', (True, '00000000')),
        ('018012345678', (True, '12345678')),
    ])
    def test_deserialization_masking(self, input, expected):
        h = websockets.FrameHeader.from_file(tutils.treader(codecs.decode(input, 'hex')))
        assert h.mask == expected[0]
        if h.mask:
            assert h.masking_key == codecs.decode(expected[1], 'hex')

    def test_equality(self):
        h = websockets.FrameHeader(mask=True, masking_key=b'1234')
        h2 = websockets.FrameHeader(mask=True, masking_key=b'1234')
        assert h == h2

        h = websockets.FrameHeader(fin=True)
        h2 = websockets.FrameHeader(fin=False)
        assert h != h2

        assert h != 'foobar'

    def test_roundtrip(self):
        def round(*args, **kwargs):
            h = websockets.FrameHeader(*args, **kwargs)
            h2 = websockets.FrameHeader.from_file(tutils.treader(bytes(h)))
            assert h == h2

        round()
        round(fin=True)
        round(rsv1=True)
        round(rsv2=True)
        round(rsv3=True)
        round(payload_length=1)
        round(payload_length=100)
        round(payload_length=1000)
        round(payload_length=10000)
        round(opcode=websockets.OPCODE.PING)
        round(masking_key=b"test")

    def test_human_readable(self):
        f = websockets.FrameHeader(
            masking_key=b"test",
            fin=True,
            payload_length=10
        )
        assert repr(f)

        f = websockets.FrameHeader()
        assert repr(f)

    def test_funky(self):
        f = websockets.FrameHeader(masking_key=b"test", mask=False)
        raw = bytes(f)
        f2 = websockets.FrameHeader.from_file(tutils.treader(raw))
        assert not f2.mask

    def test_violations(self):
        tutils.raises("opcode", websockets.FrameHeader, opcode=17)
        tutils.raises("masking key", websockets.FrameHeader, masking_key=b"x")

    def test_automask(self):
        f = websockets.FrameHeader(mask=True)
        assert f.masking_key

        f = websockets.FrameHeader(masking_key=b"foob")
        assert f.mask

        f = websockets.FrameHeader(masking_key=b"foob", mask=0)
        assert not f.mask
        assert f.masking_key


class TestFrame(object):
    def test_equality(self):
        f = websockets.Frame(payload=b'1234')
        f2 = websockets.Frame(payload=b'1234')
        assert f == f2

        assert f != b'1234'

    def test_roundtrip(self):
        def round(*args, **kwargs):
            f = websockets.Frame(*args, **kwargs)
            raw = bytes(f)
            f2 = websockets.Frame.from_file(tutils.treader(raw))
            assert f == f2
        round(b"test")
        round(b"test", fin=1)
        round(b"test", rsv1=1)
        round(b"test", opcode=websockets.OPCODE.PING)
        round(b"test", masking_key=b"test")

    def test_human_readable(self):
        f = websockets.Frame()
        assert repr(f)

        f = websockets.Frame(b"foobar")
        assert "foobar" in repr(f)

    @pytest.mark.parametrize("masked", [True, False])
    @pytest.mark.parametrize("length", [100, 50000, 150000])
    def test_serialization_bijection(self, masked, length):
        frame = websockets.Frame(
            os.urandom(length),
            fin=True,
            opcode=websockets.OPCODE.TEXT,
            mask=int(masked),
            masking_key=(os.urandom(4) if masked else None)
        )
        serialized = bytes(frame)
        assert frame == websockets.Frame.from_bytes(serialized)
