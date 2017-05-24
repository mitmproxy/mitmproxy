import os
import requests
import pytest

from mitmproxy.test import tutils
from pathod import test
from pathod.pathod import SSLOptions, CA_CERT_NAME


class TestDaemonManual:

    def test_simple(self):
        with test.Daemon() as d:
            rsp = requests.get("http://localhost:%s/p/202:da" % d.port)
            assert rsp.ok
            assert rsp.status_code == 202
        with pytest.raises(requests.ConnectionError):
            requests.get("http://localhost:%s/p/202:da" % d.port)

    @pytest.mark.parametrize('not_after_connect', [True, False])
    def test_startstop_ssl(self, not_after_connect):
        ssloptions = SSLOptions(
            cn=b'localhost',
            sans=[b'localhost', b'127.0.0.1'],
            not_after_connect=not_after_connect,
        )
        d = test.Daemon(ssl=True, ssloptions=ssloptions)
        rsp = requests.get(
            "https://localhost:%s/p/202:da" % d.port,
            verify=os.path.join(d.thread.server.ssloptions.confdir, CA_CERT_NAME))
        assert rsp.ok
        assert rsp.status_code == 202
        d.shutdown()
        with pytest.raises(requests.ConnectionError):
            requests.get("http://localhost:%s/p/202:da" % d.port)
