import mock, socket, os, time
from libmproxy import dump
from netlib import certutils, tcp
from libpathod.pathoc import Pathoc
import tutils

def get_free_port():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port


class AppTestMixin(object):
    def request(self, spec):
        t_start = time.time()
        while (time.time() - t_start) < 5:
            try:
                p = Pathoc(("127.0.0.1", self.port))
                p.connect()  # might fail as the server might not be online yet.
                return p.request(spec)
            except tcp.NetLibError:
                time.sleep(0.01)
        assert False


    def test_basic(self):
        assert self.request("get:/").status_code == 200
        assert self.request("get:/").status_code == 200  # Check for connection close
        assert len(self.m.apps.apps) == 0

    def test_cert(self):
        with tutils.tmpdir() as d:
            # Create Certs
            path = os.path.join(d, "test")
            assert certutils.dummy_ca(path)
            self.m.server.config.cacert = path

            for ext in ["pem", "p12"]:
                resp = self.request("get:/cert/%s" % ext)
                assert resp.status_code == 200
                with open(path + "-cert.%s" % ext, "rb") as f:
                    assert resp.content == f.read()

class TestAppExternal(AppTestMixin):
    @classmethod
    def setupAll(cls):
        cls.port = get_free_port()
        o = dump.Options(app=True, app_external=True, app_host="127.0.0.1", app_port=cls.port)
        s = mock.MagicMock()
        cls.m = dump.DumpMaster(s, o, None)


    @classmethod
    def teardownAll(cls):
        cls.m.shutdown()