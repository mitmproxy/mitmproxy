import tornado.testing

from mitmproxy import proxy
from mitmproxy.tools.web import app
from mitmproxy.tools.web import master as webmaster


class TestApp(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        o = webmaster.Options()
        m = webmaster.WebMaster(o, proxy.DummyServer())
        return app.Application(m, None, None)

    def test_index(self):
        assert self.fetch("/").code == 200

    def test_filter_help(self):
        assert self.fetch("/filter-help").code == 200

    def test_events(self):
        assert self.fetch("/events").code == 200

    def test_flows(self):
        assert self.fetch("/flows").code == 200
