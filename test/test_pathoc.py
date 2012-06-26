import json
from libpathod import pathoc, test, version
import tutils



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

    def test_info(self):
        c = pathoc.Pathoc("127.0.0.1", self.d.port)
        c.connect()
        _, _, _, _, content = c.request("get:/api/info")
        assert tuple(json.loads(content)["version"]) == version.IVERSION

