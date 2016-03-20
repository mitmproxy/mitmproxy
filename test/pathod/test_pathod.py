from six.moves import cStringIO as StringIO
import pytest

from pathod import pathod, version
from netlib import tcp, http
from netlib.exceptions import HttpException, TlsException
import tutils


class TestPathod(object):

    def test_logging(self):
        s = StringIO()
        p = pathod.Pathod(("127.0.0.1", 0), logfp=s)
        assert len(p.get_log()) == 0
        id = p.add_log(dict(s="foo"))
        assert p.log_by_id(id)
        assert len(p.get_log()) == 1
        p.clear_log()
        assert len(p.get_log()) == 0

        for _ in range(p.LOGBUF + 1):
            p.add_log(dict(s="foo"))
        assert len(p.get_log()) <= p.LOGBUF


class TestNoWeb(tutils.DaemonTests):
    noweb = True

    def test_noweb(self):
        assert self.get("200:da").status_code == 200
        assert self.getpath("/").status_code == 800


class TestTimeout(tutils.DaemonTests):
    timeout = 0.01

    def test_noweb(self):
        # FIXME: Add float values to spec language, reduce test timeout to
        # increase test performance
        # This is a bodge - we have some platform difference that causes
        # different exceptions to be raised here.
        tutils.raises(Exception, self.pathoc, ["get:/:p1,1"])
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
    ssloptions = dict(
        not_after_connect=True
    )

    def test_connect(self):
        r, _ = self.pathoc(
            [r"get:'http://foo.com/p/202':da"],
            connect_to=("localhost", self.d.port)
        )
        assert r[0].status_code == 202


class TestCustomCert(tutils.DaemonTests):
    ssl = True
    ssloptions = dict(
        certs=[("*", tutils.test_data.path("data/testkey.pem"))],
    )

    def test_connect(self):
        r, _ = self.pathoc([r"get:/p/202"])
        r = r[0]
        assert r.status_code == 202
        assert r.sslinfo
        assert "test.com" in str(r.sslinfo.certchain[0].get_subject())


class TestSSLCN(tutils.DaemonTests):
    ssl = True
    ssloptions = dict(
        cn="foo.com"
    )

    def test_connect(self):
        r, _ = self.pathoc([r"get:/p/202"])
        r = r[0]
        assert r.status_code == 202
        assert r.sslinfo
        assert r.sslinfo.certchain[0].get_subject().CN == "foo.com"


class TestNohang(tutils.DaemonTests):
    nohang = True

    def test_nohang(self):
        r = self.get("200:p0,0")
        assert r.status_code == 800
        l = self.d.last_log()
        assert "Pauses have been disabled" in l["response"]["msg"]


class TestHexdump(tutils.DaemonTests):
    hexdump = True

    def test_hexdump(self):
        r = self.get(r"200:b'\xf0'")


class TestNocraft(tutils.DaemonTests):
    nocraft = True

    def test_nocraft(self):
        r = self.get(r"200:b'\xf0'")
        assert r.status_code == 800
        assert "Crafting disabled" in r.content


class CommonTests(tutils.DaemonTests):

    def test_binarydata(self):
        r = self.get(r"200:b'\xf0'")
        l = self.d.last_log()
        # FIXME: Other binary data elements

    def test_sizelimit(self):
        r = self.get("200:b@1g")
        assert r.status_code == 800
        l = self.d.last_log()
        assert "too large" in l["response"]["msg"]

    def test_preline(self):
        r, _ = self.pathoc([r"get:'/p/200':i0,'\r\n'"])
        assert r[0].status_code == 200

    def test_info(self):
        assert tuple(self.d.info()["version"]) == version.IVERSION

    @pytest.mark.xfail
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
        c = tcp.TCPClient(("localhost", self.d.port))
        c.connect()
        if self.ssl:
            c.convert_to_ssl()
        c.wfile.write("foo\n\n\n")
        c.wfile.flush()
        l = self.d.last_log()
        assert l["type"] == "error"
        assert "foo" in l["msg"]

    def test_invalid_content_length(self):
        tutils.raises(
            HttpException,
            self.pathoc,
            ["get:/:h'content-length'='foo'"]
        )
        l = self.d.last_log()
        assert l["type"] == "error"
        assert "Unparseable Content Length" in l["msg"]

    def test_invalid_headers(self):
        tutils.raises(HttpException, self.pathoc, ["get:/:h'\t'='foo'"])
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
        r, _ = self.pathoc([r"get:'http://foo.com/p/202':da"])
        assert r[0].status_code == 202

    def test_websocket(self):
        r, _ = self.pathoc(["ws:/p/"], ws_read_limit=0)
        assert r[0].status_code == 101

        r, _ = self.pathoc(["ws:/p/ws"], ws_read_limit=0)
        assert r[0].status_code == 101

    def test_websocket_frame(self):
        r, _ = self.pathoc(
            ["ws:/p/", "wf:f'wf:b\"test\"':pa,1"],
            ws_read_limit=1
        )
        assert r[1].payload == "test"

    @pytest.mark.xfail
    def test_websocket_frame_reflect_error(self):
        r, _ = self.pathoc(
            ["ws:/p/", "wf:-mask:knone:f'wf:b@10':i13,'a'"],
            ws_read_limit=1,
            timeout=1
        )
        # FIXME: Race Condition?
        assert "Parse error" in self.d.text_log()

    def test_websocket_frame_disconnect_error(self):
        self.pathoc(["ws:/p/", "wf:b@10:d3"], ws_read_limit=0)
        assert self.d.last_log()


class TestDaemon(CommonTests):
    ssl = False

    def test_connect(self):
        r, _ = self.pathoc(
            [r"get:'http://foo.com/p/202':da"],
            connect_to=("localhost", self.d.port),
            ssl=True
        )
        assert r[0].status_code == 202

    def test_connect_err(self):
        tutils.raises(
            HttpException,
            self.pathoc,
            [r"get:'http://foo.com/p/202':da"],
            connect_to=("localhost", self.d.port)
        )


class TestDaemonSSL(CommonTests):
    ssl = True

    def test_ssl_conn_failure(self):
        c = tcp.TCPClient(("localhost", self.d.port))
        c.rbufsize = 0
        c.wbufsize = 0
        c.connect()
        c.wfile.write("\0\0\0\0")
        tutils.raises(TlsException, c.convert_to_ssl)
        l = self.d.last_log()
        assert l["type"] == "error"
        assert "SSL" in l["msg"]

    def test_ssl_cipher(self):
        r, _ = self.pathoc([r"get:/p/202"])
        assert r[0].status_code == 202
        assert self.d.last_log()["cipher"][1] > 0


class TestHTTP2(tutils.DaemonTests):
    ssl = True
    noweb = True
    noapi = True
    nohang = True

    if tcp.HAS_ALPN:

        def test_http2(self):
            r, _ = self.pathoc(["GET:/"], ssl=True, use_http2=True)
            assert r[0].status_code == 800
