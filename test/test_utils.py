import textwrap, cStringIO, os, time
import libpry
from libmproxy import utils


class uformat_timestamp(libpry.AutoTree):
    def test_simple(self):
        assert utils.format_timestamp(time.time())


class uisBin(libpry.AutoTree):
    def test_simple(self):
        assert not utils.isBin("testing\n\r")
        assert utils.isBin("testing\x01")
        assert utils.isBin("testing\x0e")
        assert utils.isBin("testing\x7f")


class uhexdump(libpry.AutoTree):
    def test_simple(self):
        assert utils.hexdump("one\0"*10)


class upretty_size(libpry.AutoTree):
    def test_simple(self):
        assert utils.pretty_size(100) == "100B"
        assert utils.pretty_size(1024) == "1kB"
        assert utils.pretty_size(1024 + (1024/2)) == "1.5kB"
        assert utils.pretty_size(1024*1024) == "1M"


class uData(libpry.AutoTree):
    def test_nonexistent(self):
        libpry.raises("does not exist", utils.data.path, "nonexistent")


class uMultiDict(libpry.AutoTree):
    def setUp(self):
        self.md = utils.MultiDict()

    def test_setget(self):
        assert not self.md.has_key("foo")
        self.md.append("foo", 1)
        assert self.md["foo"] == [1]
        assert self.md.has_key("foo")

    def test_del(self):
        self.md.append("foo", 1)
        del self.md["foo"]
        assert not self.md.has_key("foo")

    def test_extend(self):
        self.md.append("foo", 1)
        self.md.extend("foo", [2, 3])
        assert self.md["foo"] == [1, 2, 3]

    def test_extend_err(self):
        self.md.append("foo", 1)
        libpry.raises("not iterable", self.md.extend, "foo", 2)

    def test_get(self):
        self.md.append("foo", 1)
        self.md.append("foo", 2)
        assert self.md.get("foo") == [1, 2]
        assert self.md.get("bar") == None

    def test_caseSensitivity(self):
        self.md._helper = (utils._caseless,)
        self.md["foo"] = [1]
        self.md.append("FOO", 2)
        assert self.md["foo"] == [1, 2]
        assert self.md["FOO"] == [1, 2]
        assert self.md.has_key("FoO")

    def test_dict(self):
        self.md.append("foo", 1)
        self.md.append("foo", 2)
        self.md["bar"] = [3]
        assert self.md == self.md
        assert dict(self.md) == self.md

    def test_copy(self):
        self.md["foo"] = [1, 2]
        self.md["bar"] = [3, 4]
        md2 = self.md.copy()
        assert md2 == self.md
        assert id(md2) != id(self.md)

    def test_clear(self):
        self.md["foo"] = [1, 2]
        self.md["bar"] = [3, 4]
        self.md.clear()
        assert not self.md.keys()

    def test_setitem(self):
        libpry.raises(ValueError, self.md.__setitem__, "foo", "bar")
        self.md["foo"] = ["bar"]
        assert self.md["foo"] == ["bar"]

    def test_itemPairs(self):
        self.md.append("foo", 1)
        self.md.append("foo", 2)
        self.md.append("bar", 3)
        l = list(self.md.itemPairs())
        assert len(l) == 3
        assert ("foo", 1) in l
        assert ("foo", 2) in l
        assert ("bar", 3) in l

    def test_getset_state(self):
        self.md.append("foo", 1)
        self.md.append("foo", 2)
        self.md.append("bar", 3)
        state = self.md.get_state()
        nd = utils.MultiDict.from_state(state)
        assert nd == self.md


class uHeaders(libpry.AutoTree):
    def setUp(self):
        self.hd = utils.Headers()

    def test_read_simple(self):
        data = """
            Header: one
            Header2: two
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = cStringIO.StringIO(data)
        self.hd.read(s)
        assert self.hd["header"] == ["one"]
        assert self.hd["header2"] == ["two"]

    def test_read_multi(self):
        data = """
            Header: one
            Header: two
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = cStringIO.StringIO(data)
        self.hd.read(s)
        assert self.hd["header"] == ["one", "two"]

    def test_read_continued(self):
        data = """
            Header: one
            \ttwo
            Header2: three
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = cStringIO.StringIO(data)
        self.hd.read(s)
        assert self.hd["header"] == ['one\r\n two']

    def test_dictToHeader1(self):
        self.hd.append("one", "uno")
        self.hd.append("two", "due")
        self.hd.append("two", "tre")
        expected = [
            "one: uno\r\n",
            "two: due\r\n",
            "two: tre\r\n",
            "\r\n"
        ]
        out = repr(self.hd)
        for i in expected:
            assert out.find(i) >= 0
        
    def test_dictToHeader2(self):
        self.hd["one"] = ["uno"]
        expected1 = "one: uno\r\n"
        expected2 = "\r\n"
        out = repr(self.hd)
        assert out.find(expected1) >= 0
        assert out.find(expected2) >= 0

    def test_match_re(self):
        h = utils.Headers()
        h.append("one", "uno")
        h.append("two", "due")
        h.append("two", "tre")
        assert h.match_re("uno")
        assert h.match_re("two: due")
        assert not h.match_re("nonono")

    def test_getset_state(self):
        self.hd.append("foo", 1)
        self.hd.append("foo", 2)
        self.hd.append("bar", 3)
        state = self.hd.get_state()
        nd = utils.Headers.from_state(state)
        assert nd == self.hd


class uisStringLike(libpry.AutoTree):
    def test_all(self):
        assert utils.isStringLike("foo")
        assert not utils.isStringLike([1, 2, 3])
        assert not utils.isStringLike((1, 2, 3))
        assert not utils.isStringLike(["1", "2", "3"])


class uisSequenceLike(libpry.AutoTree):
    def test_all(self):
        assert utils.isSequenceLike([1, 2, 3])
        assert utils.isSequenceLike((1, 2, 3))
        assert not utils.isSequenceLike("foobar")
        assert utils.isSequenceLike(["foobar", "foo"])
        x = iter([1, 2, 3])
        assert utils.isSequenceLike(x)
        assert not utils.isSequenceLike(1)


class umake_bogus_cert(libpry.AutoTree):
    def test_all(self):
        d = self.tmpdir()
        path = os.path.join(d, "foo", "cert")
        utils.make_bogus_cert(path)

        d = open(path).read()
        assert "PRIVATE KEY" in d
        assert "CERTIFICATE" in d


class uprettybody(libpry.AutoTree):
    def test_all(self):
        s = "<html><p></p></html>"
        assert utils.prettybody(s)

        s = "".join([chr(i) for i in range(256)])
        assert utils.prettybody(s)


    
tests = [
    uformat_timestamp(),
    umake_bogus_cert(),
    uisBin(),
    uhexdump(),
    upretty_size(),
    uisStringLike(),
    uisSequenceLike(),
    uMultiDict(),
    uHeaders(),
    uData(),
    uprettybody(),
]
