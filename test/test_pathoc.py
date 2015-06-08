import json
import cStringIO
import re

from netlib import tcp, http
from libpathod import pathoc, test, version, pathod, language
import tutils


def test_response():
    r = pathoc.Response("1.1", 200, "Message", {}, None, None)
    assert repr(r)


class _TestDaemon:
    ssloptions = pathod.SSLOptions()

    @classmethod
    def setUpAll(self):
        self.d = test.Daemon(
            ssl = self.ssl,
            ssloptions = self.ssloptions,
            staticdir = tutils.test_data.path("data"),
            anchors = [
                (re.compile("/anchor/.*"), language.parse_pathod("202"))
            ]
        )

    @classmethod
    def tearDownAll(self):
        self.d.shutdown()

    def setUp(self):
        self.d.clear_log()

    def test_info(self):
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            ssl = self.ssl,
            fp = None
        )
        c.connect()
        resp = c.request("get:/api/info")
        assert tuple(json.loads(resp.content)["version"]) == version.IVERSION

    def tval(
        self,
        requests,
        showreq=False,
        showresp=False,
        explain=False,
        showssl=False,
        hexdump=False,
        timeout=None,
        ignorecodes=(),
        ignoretimeout=None,
        showsummary=True
    ):
        s = cStringIO.StringIO()
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            ssl = self.ssl,
            showreq = showreq,
            showresp = showresp,
            explain = explain,
            hexdump = hexdump,
            ignorecodes = ignorecodes,
            ignoretimeout = ignoretimeout,
            showsummary = showsummary,
            fp = s
        )
        c.connect(showssl=showssl, fp=s)
        if timeout:
            c.settimeout(timeout)
        for i in requests:
            r = language.parse_pathoc(i).next()
            if explain:
                r = r.freeze(language.Settings())
            try:
                c.request(r)
            except (http.HttpError, tcp.NetLibError):
                pass
        return s.getvalue()


class TestDaemonSSL(_TestDaemon):
    ssl = True
    ssloptions = pathod.SSLOptions(
        request_client_cert=True,
        sans = ["test1.com", "test2.com"]
    )

    def test_sni(self):
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            ssl = True,
            sni = "foobar.com",
            fp = None
        )
        c.connect()
        c.request("get:/p/200")
        r = c.request("get:/api/log")
        d = json.loads(r.content)
        assert d["log"][0]["request"]["sni"] == "foobar.com"

    def test_showssl(self):
        assert "certificate chain" in self.tval(["get:/p/200"], showssl=True)

    def test_clientcert(self):
        c = pathoc.Pathoc(
            ("127.0.0.1", self.d.port),
            ssl = True,
            clientcert = tutils.test_data.path("data/clientcert/client.pem"),
            fp = None
        )
        c.connect()
        c.request("get:/p/200")
        r = c.request("get:/api/log")
        d = json.loads(r.content)
        assert d["log"][0]["request"]["clientcert"]["keyinfo"]


class TestDaemon(_TestDaemon):
    ssl = False

    def test_ssl_error(self):
        c = pathoc.Pathoc(("127.0.0.1", self.d.port), ssl = True, fp=None)
        tutils.raises("ssl handshake", c.connect)

    def test_showssl(self):
        assert not "certificate chain" in self.tval(
            ["get:/p/200"],
            showssl=True)

    def test_ignorecodes(self):
        assert "200" in self.tval(["get:'/p/200:b@1'"])
        assert "200" in self.tval(["get:'/p/200:b@1'"])
        assert "200" in self.tval(["get:'/p/200:b@1'"])
        assert "200" not in self.tval(["get:'/p/200:b@1'"], ignorecodes=[200])
        assert "200" not in self.tval(
            ["get:'/p/200:b@1'"],
            ignorecodes=[
                200,
                201])
        assert "202" in self.tval(["get:'/p/202:b@1'"], ignorecodes=[200, 201])

    def test_timeout(self):
        assert "Timeout" in self.tval(["get:'/p/200:p0,100'"], timeout=0.01)
        assert "HTTP" in self.tval(
            ["get:'/p/200:p5,100'"],
            showresp=True,
            timeout=0.01
        )
        assert not "HTTP" in self.tval(
            ["get:'/p/200:p3,10'"],
            showresp=True,
            timeout=0.01,
            ignoretimeout=True
        )

    def test_showresp(self):
        reqs = ["get:/api/info:p0,0", "get:/api/info:p0,0"]
        assert self.tval(reqs).count("200") == 2
        assert self.tval(reqs, showresp=True).count("HTTP/1.1 200 OK") == 2
        assert self.tval(
            reqs, showresp=True, hexdump=True
        ).count("0000000000") == 2

    def test_showresp_httperr(self):
        v = self.tval(["get:'/p/200:d20'"], showresp=True, showsummary=True)
        assert "Invalid headers" in v
        assert "HTTP/" in v

    def test_explain(self):
        reqs = ["get:/p/200:b@100"]
        assert "b@100" not in self.tval(reqs, explain=True)

    def test_showreq(self):
        reqs = ["get:/api/info:p0,0", "get:/api/info:p0,0"]
        assert self.tval(reqs, showreq=True).count("GET /api") == 2
        assert self.tval(
            reqs, showreq=True, hexdump=True
        ).count("0000000000") == 2

    def test_conn_err(self):
        assert "Invalid server response" in self.tval(["get:'/p/200:d2'"])

    def test_connect_fail(self):
        to = ("foobar", 80)
        c = pathoc.Pathoc(("127.0.0.1", self.d.port), fp=None)
        c.rfile, c.wfile = cStringIO.StringIO(), cStringIO.StringIO()
        tutils.raises("connect failed", c.http_connect, to)
        c.rfile = cStringIO.StringIO(
            "HTTP/1.1 500 OK\r\n"
        )
        tutils.raises("connect failed", c.http_connect, to)
        c.rfile = cStringIO.StringIO(
            "HTTP/1.1 200 OK\r\n"
        )
        c.http_connect(to)
