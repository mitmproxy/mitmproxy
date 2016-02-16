import logging
import requests
from pathod import test
import tutils
logging.disable(logging.CRITICAL)


class TestDaemonManual:

    def test_simple(self):
        with test.Daemon() as d:
            rsp = requests.get("http://localhost:%s/p/202:da" % d.port)
            assert rsp.ok
            assert rsp.status_code == 202
        with tutils.raises(requests.ConnectionError):
            requests.get("http://localhost:%s/p/202:da" % d.port)

    def test_startstop_ssl(self):
        d = test.Daemon(ssl=True)
        rsp = requests.get(
            "https://localhost:%s/p/202:da" %
            d.port,
            verify=False)
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        with tutils.raises(requests.ConnectionError):
            requests.get("http://localhost:%s/p/202:da" % d.port)

    def test_startstop_ssl_explicit(self):
        ssloptions = dict(
            certfile=tutils.test_data.path("data/testkey.pem"),
            cacert=tutils.test_data.path("data/testkey.pem"),
            ssl_after_connect=False
        )
        d = test.Daemon(ssl=ssloptions)
        rsp = requests.get(
            "https://localhost:%s/p/202:da" %
            d.port,
            verify=False)
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        with tutils.raises(requests.ConnectionError):
            requests.get("http://localhost:%s/p/202:da" % d.port)
