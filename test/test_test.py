import time, logging
import requests
from libpathod import test, utils
import tutils

logging.disable(logging.CRITICAL)

class TestDaemonManual:
    def test_simple(self):
        with test.Daemon() as d:
            rsp = requests.get("http://localhost:%s/p/202"%d.port)
            assert rsp.ok
            assert rsp.status_code == 202
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


