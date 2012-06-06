import time
import libpry
import requests
from libpathod import test, version


class uDaemonManual(libpry.AutoTree):
    def test_startstop(self):
        d = test.Daemon()
        rsp = requests.get("http://localhost:%s/p/202"%d.port)
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        rsp = requests.get("http://localhost:%s/p/202"%d.port)
        assert not rsp.ok


class uDaemon(libpry.AutoTree):
    def setUpAll(self):
        self.d = test.Daemon()

    def tearDownAll(self):
        self.d.shutdown()

    def test_info(self):
        assert tuple(self.d.info()["version"]) == version.IVERSION



tests = [
    uDaemonManual(),
    uDaemon()
]
