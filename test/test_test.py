import time, logging
import requests
from libpathod import test, version, utils
import tutils

logging.disable(logging.CRITICAL)

class TestDaemonManual:
    def test_simple(self):
        d = test.Daemon()
        rsp = requests.get("http://localhost:%s/p/202"%d.port)
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        tutils.raises(requests.ConnectionError, requests.get, "http://localhost:%s/p/202"%d.port)

    def test_startstop_ssl(self):
        d = test.Daemon(ssl=True)
        rsp = requests.get("https://localhost:%s/p/202"%d.port, verify=False)
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        tutils.raises(requests.ConnectionError, requests.get, "http://localhost:%s/p/202"%d.port)

    def test_startstop_ssl_explicit(self):
        ssloptions = dict(
             keyfile = utils.data.path("resources/server.key"),
             certfile = utils.data.path("resources/server.crt"),
        )
        d = test.Daemon(ssl=ssloptions)
        rsp = requests.get("https://localhost:%s/p/202"%d.port, verify=False)
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        tutils.raises(requests.ConnectionError, requests.get, "http://localhost:%s/p/202"%d.port)


class TestDaemon:
    @classmethod
    def setUpAll(self):
        self.d = test.Daemon()

    @classmethod
    def tearDownAll(self):
        self.d.shutdown()

    def setUp(self):
        self.d.clear_log()

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



