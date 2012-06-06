import time
import libpry
import requests
from libpathod import test


class uDaemon(libpry.AutoTree):
    def test_startstop(self):
        d = test.Daemon()
        rsp = requests.get("http://localhost:%s/p/202"%d.port)
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        rsp = requests.get("http://localhost:%s/p/202"%d.port)
        assert not rsp.ok



tests = [
    uDaemon()
]
