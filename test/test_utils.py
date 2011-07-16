import textwrap, cStringIO, os, time, re, json
import libpry
from libmproxy import utils

utils.CERT_SLEEP_TIME = 0


class uformat_timestamp(libpry.AutoTree):
    def test_simple(self):
        assert utils.format_timestamp(utils.timestamp())


class uisBin(libpry.AutoTree):
    def test_simple(self):
        assert not utils.isBin("testing\n\r")
        assert utils.isBin("testing\x01")
        assert utils.isBin("testing\x0e")
        assert utils.isBin("testing\x7f")


class uisXML(libpry.AutoTree):
    def test_simple(self):
        assert not utils.isXML("foo")
        assert utils.isXML("<foo")
        assert utils.isXML("  \n<foo")


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
        self.hd.add("one", "uno")
        self.hd.add("two", "due")
        self.hd.add("two", "tre")
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
        h.add("one", "uno")
        h.add("two", "due")
        h.add("two", "tre")
        assert h.match_re("uno")
        assert h.match_re("two: due")
        assert not h.match_re("nonono")

    def test_getset_state(self):
        self.hd.add("foo", 1)
        self.hd.add("foo", 2)
        self.hd.add("bar", 3)
        state = self.hd.get_state()
        nd = utils.Headers.from_state(state)
        assert nd == self.hd

    def test_copy(self):
        self.hd.add("foo", 1)
        self.hd.add("foo", 2)
        self.hd.add("bar", 3)
        assert self.hd == self.hd.copy()

    def test_del(self):
        self.hd.add("foo", 1)
        self.hd.add("Foo", 2)
        self.hd.add("bar", 3)
        del self.hd["foo"]
        assert len(self.hd.lst) == 1


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



class upretty_xmlish(libpry.AutoTree):
    def test_tagre(self):
        def f(s):
            return re.search(utils.TAG, s, re.VERBOSE|re.MULTILINE)
        assert f(r"<body>")
        assert f(r"<body/>")
        assert f(r"< body/>")
        assert f(r"< body/ >")
        assert f(r"< body / >")
        assert f(r"<foo a=b>")
        assert f(r"<foo a='b'>")
        assert f(r"<foo a='b\"'>")
        assert f(r'<a b=(a.b) href="foo">')
        assert f('<td width=25%>')
        assert f('<form name="search" action="/search.php" method="get" accept-charset="utf-8" class="search">')
        assert f('<img src="gif" width="125" height="16" alt=&quot;&quot; />')


    def test_all(self):
        def isbalanced(ret):
            # The last tag should have no indent
            assert ret[-1].strip() == ret[-1]

        s = "<html><br><br></br><p>one</p></html>"
        ret = utils.pretty_xmlish(s)
        isbalanced(ret)

        s = r"""
<body bgcolor=#ffffff text=#000000 link=#0000cc vlink=#551a8b alink=#ff0000 onload="document.f.q.focus();if(document.images)new Image().src='/images/srpr/nav_logo27.png'" ><textarea id=csi style=display:none></textarea></body>
        """
        isbalanced(utils.pretty_xmlish(textwrap.dedent(s)))

        s = r"""
                <a href="http://foo.com" target="">
                   <img src="http://foo.gif" alt="bar" height="25" width="132">
                </a>
            """
        isbalanced(utils.pretty_xmlish(textwrap.dedent(s)))

        s = r"""
            <!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\"
            \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\">
            <html></html>
        """
        ret = utils.pretty_xmlish(textwrap.dedent(s))
        isbalanced(ret)

        s = "<html><br/><p>one</p></html>"
        ret = utils.pretty_xmlish(s)
        assert len(ret) == 6
        isbalanced(ret)

        s = "gobbledygook"
        assert utils.pretty_xmlish(s) == ["gobbledygook"]


class upretty_json(libpry.AutoTree):
    def test_one(self):
        s = json.dumps({"foo": 1})
        assert utils.pretty_json(s)
        assert not utils.pretty_json("moo")


class u_urldecode(libpry.AutoTree):
    def test_one(self):
        s = "one=two&three=four"
        assert len(utils.urldecode(s)) == 2


class udummy_ca(libpry.AutoTree):
    def test_all(self):
        d = self.tmpdir()
        path = os.path.join(d, "foo/cert.cnf")
        assert utils.dummy_ca(path)
        assert os.path.exists(path)

        path = os.path.join(d, "foo/cert2.pem")
        assert utils.dummy_ca(path)
        assert os.path.exists(path)
        assert os.path.exists(os.path.join(d, "foo/cert2-cert.pem"))
        assert os.path.exists(os.path.join(d, "foo/cert2-cert.p12"))


class udummy_cert(libpry.AutoTree):
    def test_with_ca(self):
        d = self.tmpdir()
        cacert = os.path.join(d, "foo/cert.cnf")
        assert utils.dummy_ca(cacert)
        assert utils.dummy_cert(
            os.path.join(d, "foo"),
            cacert,
            "foo.com"
        )
        assert os.path.exists(os.path.join(d, "foo", "foo.com.pem"))
        # Short-circuit
        assert utils.dummy_cert(
            os.path.join(d, "foo"),
            cacert,
            "foo.com"
        )

    def test_no_ca(self):
        d = self.tmpdir()
        assert utils.dummy_cert(
            d,
            None,
            "foo.com"
        )
        assert os.path.exists(os.path.join(d, "foo.com.pem"))


class uLRUCache(libpry.AutoTree):
    def test_one(self):
        class Foo:
            ran = False
            @utils.LRUCache(2)
            def one(self, x):
                self.ran = True
                return x

        f = Foo()
        assert f.one(1) == 1
        assert f.ran
        f.ran = False
        assert f.one(1) == 1
        assert not f.ran

        f.ran = False
        assert f.one(1) == 1
        assert not f.ran
        assert f.one(2) == 2
        assert f.one(3) == 3
        assert f.ran

        f.ran = False
        assert f.one(1) == 1
        assert f.ran

        assert len(f._cached_one) == 2
        assert len(f._cachelist_one) == 2


tests = [
    uformat_timestamp(),
    uisBin(),
    uisXML(),
    uhexdump(),
    upretty_size(),
    uisStringLike(),
    uisSequenceLike(),
    uHeaders(),
    uData(),
    upretty_xmlish(),
    upretty_json(),
    u_urldecode(),
    udummy_ca(),
    udummy_cert(),
    uLRUCache(),
]
