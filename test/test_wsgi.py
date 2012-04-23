import cStringIO
import libpry
from libmproxy import wsgi
import tutils


class TestApp:
    def __init__(self):
        self.called = False

    def __call__(self, environ, start_response):
        self.called = True
        status = '200 OK'
        response_headers = [('Content-type', 'text/plain')]
        start_response(status, response_headers)
        return ['Hello', ' world!\n']


class uWSGIAdaptor(libpry.AutoTree):
    def test_make_environ(self):
        w = wsgi.WSGIAdaptor(None, "foo", 80)
        assert w.make_environ(
            tutils.treq(),
            None
        )

    def test_serve(self):
        ta = TestApp()
        w = wsgi.WSGIAdaptor(ta, "foo", 80)
        r = tutils.treq()
        r.host = "foo"
        r.port = 80

        wfile = cStringIO.StringIO()
        err = w.serve(r, wfile)
        assert ta.called
        assert not err

        val = wfile.getvalue()
        assert "Hello world" in val
        assert "Server:" in val


class uAppRegistry(libpry.AutoTree):
    def test_add_get(self):
        ar = wsgi.AppRegistry()
        ar.add("foo", "domain", 80)

        r = tutils.treq()
        r.host = "domain"
        r.port = 80
        assert ar.get(r)

        r.port = 81
        assert not ar.get(r)


tests = [
    uWSGIAdaptor(),
    uAppRegistry()
]
