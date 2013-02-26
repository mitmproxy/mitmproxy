from libpathod import pathod, version
from netlib import tcp, http
import requests
import tutils

class TestPathod:
    def test_instantiation(self):
        p = pathod.Pathod(
                ("127.0.0.1", 0),
                anchors = [(".*", "200:da")]
            )
        assert p.anchors
        tutils.raises("invalid regex", pathod.Pathod, ("127.0.0.1", 0), anchors=[("*", "200:da")])
        tutils.raises("invalid page spec", pathod.Pathod, ("127.0.0.1", 0), anchors=[("foo", "bar")])

    def test_logging(self):
        p = pathod.Pathod(("127.0.0.1", 0))
        assert len(p.get_log()) == 0
        id = p.add_log(dict(s="foo"))
        assert p.log_by_id(id)
        assert len(p.get_log()) == 1
        p.clear_log()
        assert len(p.get_log()) == 0

        for i in range(p.LOGBUF + 1):
            p.add_log(dict(s="foo"))
        assert len(p.get_log()) <= p.LOGBUF


class TestNoWeb(tutils.DaemonTests):
    noweb = True
    def test_noweb(self):
        assert self.get("200:da").status_code == 200
        assert self.getpath("/").status_code == 800


class TestTimeout(tutils.DaemonTests):
    timeout = 0.00001
    def test_noweb(self):
        # FIXME: Add float values to spec language, reduce test timeout to
        # increase test performance
        tutils.raises("server disconnect", self.pathoc, "get:/:p1,1")
        assert self.d.last_log()["type"] == "timeout"


class TestNoApi(tutils.DaemonTests):
    noapi = True
    def test_noapi(self):
        assert self.getpath("/log").status_code == 404
        r = self.getpath("/")
        assert r.status_code == 200
        assert not "Log" in r.content


class TestNotAfterConnect(tutils.DaemonTests):
    ssl = False
    not_after_connect = True
    def test_connect(self):
        r = self.pathoc(r"get:'http://foo.com/p/202':da", connect_to=("localhost", self.d.port))
        assert r.status_code == 202


class TestNohang(tutils.DaemonTests):
    nohang = True
    def test_nohang(self):
        r = self.get("200:p0,0")
        assert r.status_code == 800
        l = self.d.last_log()
        assert "Pauses have been disabled" in l["msg"]


class TestHexdump(tutils.DaemonTests):
    hexdump = True
    def test_hexdump(self):
        r = self.get(r"200:b'\xf0'")


class CommonTests(tutils.DaemonTests):
    def test_binarydata(self):
        r = self.get(r"200:b'\xf0'")
        l = self.d.last_log()
        # FIXME: Other binary data elements

    def test_sizelimit(self):
        r = self.get("200:b@1g")
        assert r.status_code == 800
        l = self.d.last_log()
        assert "too large" in l["msg"]

    def test_preline(self):
        r = self.pathoc(r"get:'/p/200':i0,'\r\n'")
        assert r.status_code == 200

    def test_info(self):
        assert tuple(self.d.info()["version"]) == version.IVERSION

    def test_logs(self):
        assert self.d.clear_log()
        assert not self.d.last_log()
        rsp = self.get("202:da")
        assert len(self.d.log()) == 1
        assert self.d.clear_log()
        assert len(self.d.log()) == 0

    def test_disconnect(self):
        rsp = self.get("202:b@100k:d200")
        assert len(rsp.content) < 200

    def test_parserr(self):
        rsp = self.get("400:msg,b:")
        assert rsp.status_code == 800

    def test_static(self):
        rsp = self.get("200:b<file")
        assert rsp.status_code == 200
        assert rsp.content.strip() == "testfile"

    def test_anchor(self):
        rsp = self.getpath("anchor/foo")
        assert rsp.status_code == 202

    def test_invalid_first_line(self):
        c = tcp.TCPClient("localhost", self.d.port)
        c.connect()
        if self.ssl:
            c.convert_to_ssl()
        c.wfile.write("foo\n\n\n")
        c.wfile.flush()
        l = self.d.last_log()
        assert l["type"] == "error"
        assert "foo" in l["msg"]

    def test_invalid_body(self):
        tutils.raises(http.HttpError, self.pathoc, "get:/:h'content-length'='foo'")
        l = self.d.last_log()
        assert l["type"] == "error"
        assert "Invalid" in l["msg"]

    def test_invalid_headers(self):
        tutils.raises(http.HttpError, self.pathoc, "get:/:h'\t'='foo'")
        l = self.d.last_log()
        assert l["type"] == "error"
        assert "Invalid headers" in l["msg"]

    def test_access_denied(self):
        rsp = self.get("=nonexistent")
        assert rsp.status_code == 800

    def test_source_access_denied(self):
        rsp = self.get("200:b</foo")
        assert rsp.status_code == 800
        assert "File access denied" in rsp.content

    def test_proxy(self):
        r = self.pathoc(r"get:'http://foo.com/p/202':da")
        assert r.status_code == 202


class TestDaemon(CommonTests):
    ssl = False
    def test_connect(self):
        r = self.pathoc(r"get:'http://foo.com/p/202':da", connect_to=("localhost", self.d.port), ssl=True)
        assert r.status_code == 202

    def test_connect_err(self):
        tutils.raises(http.HttpError, self.pathoc, r"get:'http://foo.com/p/202':da", connect_to=("localhost", self.d.port))


class TestDaemonSSL(CommonTests):
    ssl = True
    def test_ssl_conn_failure(self):
        c = tcp.TCPClient("localhost", self.d.port)
        c.rbufsize = 0
        c.wbufsize = 0
        c.connect()
        try:
            while 1:
                c.wfile.write("\r\n\r\n\r\n")
        except:
            pass
        l = self.d.last_log()
        assert l["type"] == "error"
        assert "SSL" in l["msg"]



