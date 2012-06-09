import cStringIO, sys
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


class TestWSGIAdaptor:
    def test_make_environ(self):
        w = wsgi.WSGIAdaptor(None, "foo", 80)
        tr = tutils.treq()
        assert w.make_environ(tr, None)

        tr.path = "/foo?bar=voing"
        r = w.make_environ(tr, None)
        assert r["QUERY_STRING"] == "bar=voing"

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

    def _serve(self, app):
        w = wsgi.WSGIAdaptor(app, "foo", 80)
        r = tutils.treq()
        r.host = "foo"
        r.port = 80
        wfile = cStringIO.StringIO()
        err = w.serve(r, wfile)
        return wfile.getvalue()

    def test_serve_empty_body(self):
        def app(environ, start_response):
            status = '200 OK'
            response_headers = [('Foo', 'bar')]
            start_response(status, response_headers)
            return []
        assert self._serve(app)

    def test_serve_double_start(self):
        def app(environ, start_response):
            try:
                raise ValueError("foo")
            except:
                ei = sys.exc_info()
            status = '200 OK'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            start_response(status, response_headers)
        assert "Internal Server Error" in self._serve(app)

    def test_serve_single_err(self):
        def app(environ, start_response):
            try:
                raise ValueError("foo")
            except:
                ei = sys.exc_info()
            status = '200 OK'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers, ei)
        assert "Internal Server Error" in self._serve(app)

    def test_serve_double_err(self):
        def app(environ, start_response):
            try:
                raise ValueError("foo")
            except:
                ei = sys.exc_info()
            status = '200 OK'
            response_headers = [('Content-type', 'text/plain')]
            start_response(status, response_headers)
            yield "aaa"
            start_response(status, response_headers, ei)
            yield "bbb"
        assert "Internal Server Error" in self._serve(app)


class TestAppRegistry:
    def test_add_get(self):
        ar = wsgi.AppRegistry()
        ar.add("foo", "domain", 80)

        r = tutils.treq()
        r.host = "domain"
        r.port = 80
        assert ar.get(r)

        r.port = 81
        assert not ar.get(r)
