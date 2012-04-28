import libpry
from libpathod import app
from tornado import httpserver


class uApplication(libpry.AutoTree):
    def dummy_page(self, path):
        # A hideous, hideous kludge, but Tornado seems to have no more sensible
        # way to do this.
        a = app.PathodApp(staticdir=None)
        for h in a.handlers[0][1]:
            if h.regex.match(path):
                klass = h.handler_class
        r = httpserver.HTTPRequest("GET", path)
        del r.connection
        return klass(a, r)

    def test_create(self):
        assert app.PathodApp(staticdir=None)

    def test_index(self):
        page = self.dummy_page("/")
        page.get()
        assert "".join(page._write_buffer)

    def test_help(self):
        page = self.dummy_page("/help")
        page.get()
        assert "".join(page._write_buffer)



tests = [
    uApplication()
]
