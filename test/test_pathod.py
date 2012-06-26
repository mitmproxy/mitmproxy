import requests
from libpathod import pathod, test, version
import tutils

class _TestApplication:
    def test_anchors(self):
        a = pathod.PathodApp(staticdir=None)
        a.add_anchor("/foo", "200")
        assert a.get_anchors() == [("/foo", "200")]
        a.add_anchor("/bar", "400")
        assert a.get_anchors() == [("/bar", "400"), ("/foo", "200")]
        a.remove_anchor("/bar", "400")
        assert a.get_anchors() == [("/foo", "200")]
        a.remove_anchor("/oink", "400")
        assert a.get_anchors() == [("/foo", "200")]


class TestPathod:
    def test_instantiation(self):
        p = pathod.Pathod(
                ("127.0.0.1", 0),
                anchors = [(".*", "200")]
            )
        assert p.anchors
        tutils.raises("invalid regex", pathod.Pathod, ("127.0.0.1", 0), anchors=[("*", "200")])
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


class TestDaemon:
    @classmethod
    def setUpAll(self):
        self.d = test.Daemon(
            staticdir=tutils.test_data.path("data"),
            anchors=[("/anchor/.*", "202")]
        )

    @classmethod
    def tearDownAll(self):
        self.d.shutdown()

    def setUp(self):
        self.d.clear_log()

    def getpath(self, path):
        return requests.get("http://localhost:%s/%s"%(self.d.port, path))

    def get(self, spec):
        return requests.get("http://localhost:%s/p/%s"%(self.d.port, spec))

    def test_info(self):
        assert tuple(self.d.info()["version"]) == version.IVERSION

    def test_logs(self):
        rsp = self.get("202")
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
