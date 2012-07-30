import requests
from libpathod import test

class Test:
    def setUp(self):
        self.daemon = test.Daemon()

    def tearDown(self):
        self.daemon.shutdown()

    def test_simple(self):
        path = self.daemon.p("200:b@100")
        r = requests.get(path)
        assert r.status_code == 200
        assert len(r.content) == 100
        log = self.daemon.last_log()
        assert log["request"]["method"] == "GET"
