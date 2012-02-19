import textwrap, os, re, json
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


class udel_all(libpry.AutoTree):
    def test_simple(self):
        d = dict(a=1, b=2, c=3)
        utils.del_all(d, ["a", "x", "b"])
        assert d.keys() == ["c"]


class uclean_hanging_newline(libpry.AutoTree):
    def test_simple(self):
        s = "foo\n"
        assert utils.clean_hanging_newline(s) == "foo"
        assert utils.clean_hanging_newline("foo") == "foo"


class upretty_size(libpry.AutoTree):
    def test_simple(self):
        assert utils.pretty_size(100) == "100B"
        assert utils.pretty_size(1024) == "1kB"
        assert utils.pretty_size(1024 + (1024/2.0)) == "1.5kB"
        assert utils.pretty_size(1024*1024) == "1M"


class uData(libpry.AutoTree):
    def test_nonexistent(self):
        libpry.raises("does not exist", utils.pkg_data.path, "nonexistent")



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
        p = utils.dummy_cert(
            os.path.join(d, "foo"),
            cacert,
            "foo.com"
        )
        assert os.path.exists(p)
        # Short-circuit
        assert utils.dummy_cert(
            os.path.join(d, "foo"),
            cacert,
            "foo.com"
        )

    def test_no_ca(self):
        d = self.tmpdir()
        p = utils.dummy_cert(
            d,
            None,
            "foo.com"
        )
        assert os.path.exists(p)


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


class u_parse_proxy_spec(libpry.AutoTree):
    def test_simple(self):
        assert not utils.parse_proxy_spec("")
        assert utils.parse_proxy_spec("http://foo.com:88") == ("http", "foo.com", 88)
        assert utils.parse_proxy_spec("http://foo.com") == ("http", "foo.com", 80)
        assert not utils.parse_proxy_spec("foo.com")
        assert not utils.parse_proxy_spec("http://")


class u_unparse_url(libpry.AutoTree):
    def test_simple(self):
        assert utils.unparse_url("http", "foo.com", 99, "") == "http://foo.com:99"
        assert utils.unparse_url("http", "foo.com", 80, "") == "http://foo.com"
        assert utils.unparse_url("https", "foo.com", 80, "") == "https://foo.com:80"
        assert utils.unparse_url("https", "foo.com", 443, "") == "https://foo.com"


class u_parse_url(libpry.AutoTree):
    def test_simple(self):
        assert not utils.parse_url("")

        u = "http://foo.com:8888/test"
        s, h, po, pa = utils.parse_url(u)
        assert s == "http"
        assert h == "foo.com"
        assert po == 8888
        assert pa == "/test"

        s, h, po, pa = utils.parse_url("http://foo/bar")
        assert s == "http"
        assert h == "foo"
        assert po == 80
        assert pa == "/bar"

        s, h, po, pa = utils.parse_url("http://foo")
        assert pa == "/"

        s, h, po, pa = utils.parse_url("https://foo")
        assert po == 443

        assert not utils.parse_url("https://foo:bar")
        assert not utils.parse_url("https://foo:")


class u_parse_size(libpry.AutoTree):
    def test_simple(self):
        assert not utils.parse_size("")
        assert utils.parse_size("1") == 1
        assert utils.parse_size("1k") == 1024
        assert utils.parse_size("1m") == 1024**2
        assert utils.parse_size("1g") == 1024**3
        libpry.raises(ValueError, utils.parse_size, "1f")
        libpry.raises(ValueError, utils.parse_size, "ak")


tests = [
    uformat_timestamp(),
    uisBin(),
    uisXML(),
    uhexdump(),
    upretty_size(),
    uData(),
    upretty_xmlish(),
    upretty_json(),
    u_urldecode(),
    udel_all(),
    udummy_ca(),
    udummy_cert(),
    uLRUCache(),
    u_parse_url(),
    u_parse_proxy_spec(),
    u_unparse_url(),
    u_parse_size(),
    uclean_hanging_newline()
]
