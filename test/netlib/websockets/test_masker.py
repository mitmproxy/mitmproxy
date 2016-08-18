import codecs
import pytest

from netlib import websockets


class TestMasker(object):

    @pytest.mark.parametrize("input,expected", [
        ([b"a"], '00'),
        ([b"four"], '070d1616'),
        ([b"fourf"], '070d161607'),
        ([b"fourfive"], '070d1616070b1501'),
        ([b"a", b"aasdfasdfa", b"asdf"], '000302170504021705040205120605'),
        ([b"a" * 50, b"aasdfasdfa", b"asdf"], '00030205000302050003020500030205000302050003020500030205000302050003020500030205000302050003020500030205120605051206050500110702'),  # noqa
    ])
    def test_masker(self, input, expected):
        m = websockets.Masker(b"abcd")
        data = b"".join([m(t) for t in input])
        assert data == codecs.decode(expected, 'hex')

        data = websockets.Masker(b"abcd")(data)
        assert data == b"".join(input)
