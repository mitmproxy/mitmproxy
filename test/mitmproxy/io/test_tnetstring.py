import unittest
import random
import math
import io
import struct

from mitmproxy.io import tnetstring

MAXINT = 2 ** (struct.Struct('i').size * 8 - 1) - 1

FORMAT_EXAMPLES = {
    b'0:}': {},
    b'0:]': [],
    b'51:5:hello,39:11:12345678901#4:this,4:true!0:~4:\x00\x00\x00\x00,]}':
    {b'hello': [12345678901, b'this', True, None, b'\x00\x00\x00\x00']},
    b'5:12345#': 12345,
    b'12:this is cool,': b'this is cool',
    b'19:this is unicode \xe2\x98\x85;': 'this is unicode \u2605',
    b'0:,': b'',
    b'0:;': '',
    b'0:~': None,
    b'4:true!': True,
    b'5:false!': False,
    b'10:\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00,': b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
    b'24:5:12345#5:67890#5:xxxxx,]': [12345, 67890, b'xxxxx'],
    b'18:3:0.1^3:0.2^3:0.3^]': [0.1, 0.2, 0.3],
    b'243:238:233:228:223:218:213:208:203:198:193:188:183:178:173:168:163:158:153:148:143:138:133:128:123:118:113:108:103:99:95:91:87:83:79:75:71:67:63:59:55:51:47:43:39:35:31:27:23:19:15:11:hello-there,]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]': [[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[b'hello-there']]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]  # noqa
}


def get_random_object(random=random, depth=0):
    """Generate a random serializable object."""
    #  The probability of generating a scalar value increases as the depth increase.
    #  This ensures that we bottom out eventually.
    if random.randint(depth, 10) <= 4:
        what = random.randint(0, 1)
        if what == 0:
            n = random.randint(0, 10)
            l = []
            for _ in range(n):
                l.append(get_random_object(random, depth + 1))
            return l
        if what == 1:
            n = random.randint(0, 10)
            d = {}
            for _ in range(n):
                n = random.randint(0, 100)
                k = str([random.randint(32, 126) for _ in range(n)])
                d[k] = get_random_object(random, depth + 1)
            return d
    else:
        what = random.randint(0, 4)
        if what == 0:
            return None
        if what == 1:
            return True
        if what == 2:
            return False
        if what == 3:
            if random.randint(0, 1) == 0:
                return random.randint(0, MAXINT)
            else:
                return -1 * random.randint(0, MAXINT)
        n = random.randint(0, 100)
        return bytes([random.randint(32, 126) for _ in range(n)])


class Test_Format(unittest.TestCase):

    def test_roundtrip_format_examples(self):
        for data, expect in FORMAT_EXAMPLES.items():
            self.assertEqual(expect, tnetstring.loads(data))
            self.assertEqual(
                expect, tnetstring.loads(tnetstring.dumps(expect)))
            self.assertEqual((expect, b''), tnetstring.pop(data))

    def test_roundtrip_format_random(self):
        for _ in range(10):
            v = get_random_object()
            self.assertEqual(v, tnetstring.loads(tnetstring.dumps(v)))
            self.assertEqual((v, b""), tnetstring.pop(tnetstring.dumps(v)))

    def test_roundtrip_format_unicode(self):
        for _ in range(10):
            v = get_random_object()
            self.assertEqual(v, tnetstring.loads(tnetstring.dumps(v)))
            self.assertEqual((v, b''), tnetstring.pop(tnetstring.dumps(v)))

    def test_roundtrip_big_integer(self):
        i1 = math.factorial(30000)
        s = tnetstring.dumps(i1)
        i2 = tnetstring.loads(s)
        self.assertEqual(i1, i2)


class Test_FileLoading(unittest.TestCase):

    def test_roundtrip_file_examples(self):
        for data, expect in FORMAT_EXAMPLES.items():
            s = io.BytesIO()
            s.write(data)
            s.write(b'OK')
            s.seek(0)
            self.assertEqual(expect, tnetstring.load(s))
            self.assertEqual(b'OK', s.read())
            s = io.BytesIO()
            tnetstring.dump(expect, s)
            s.write(b'OK')
            s.seek(0)
            self.assertEqual(expect, tnetstring.load(s))
            self.assertEqual(b'OK', s.read())

    def test_roundtrip_file_random(self):
        for _ in range(10):
            v = get_random_object()
            s = io.BytesIO()
            tnetstring.dump(v, s)
            s.write(b'OK')
            s.seek(0)
            self.assertEqual(v, tnetstring.load(s))
            self.assertEqual(b'OK', s.read())

    def test_error_on_absurd_lengths(self):
        s = io.BytesIO()
        s.write(b'1000000000:pwned!,')
        s.seek(0)
        with self.assertRaises(ValueError):
            tnetstring.load(s)
        self.assertEqual(s.read(1), b':')


def suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(Test_Format))
    suite.addTest(loader.loadTestsFromTestCase(Test_FileLoading))
    return suite
