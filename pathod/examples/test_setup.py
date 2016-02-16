import requests
from pathod import test


class Test:

    """
        Testing the requests module with
        a pathod instance started for
        each test.
    """

    def setup(self):
        self.d = test.Daemon()

    def teardown(self):
        self.d.shutdown()

    def test_simple(self):
        # Get a URL for a pathod spec
        url = self.d.p("200:b@100")
        # ... and request it
        r = requests.put(url)

        # Check the returned data
        assert r.status_code == 200
        assert len(r.content) == 100

        # Check pathod's internal log
        log = self.d.last_log()["request"]
        assert log["method"] == "PUT"
