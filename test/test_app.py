import libpry
from libpathod import app
from tornado import httpserver

class uApplication(libpry.AutoTree):
    def test_anchors(self):
        a = app.PathodApp(staticdir=None)
        a.add_anchor("/foo", "200")
        assert a.get_anchors() == [("/foo", "200")]
        a.add_anchor("/bar", "400")
        assert a.get_anchors() == [("/bar", "400"), ("/foo", "200")]
        a.remove_anchor("/bar", "400")
        assert a.get_anchors() == [("/foo", "200")]
        a.remove_anchor("/oink", "400")
        assert a.get_anchors() == [("/foo", "200")]

    def test_logs(self):
        a = app.PathodApp(staticdir=None)
        a.LOGBUF = 3
        a.add_log({})
        assert a.log[0]["id"] == 0
        a.add_log({})
        a.add_log({})
        assert a.log[0]["id"] == 2
        a.add_log({})
        assert len(a.log) == 3
        assert a.log[0]["id"] == 3
        assert a.log[-1]["id"] == 1

        assert a.log_by_id(1)["id"] == 1
        assert not a.log_by_id(0)



class uPages(libpry.AutoTree):
    def dummy_page(self, path):
        # A hideous, hideous kludge, but Tornado seems to have no more sensible
        # way to do this.
        a = app.PathodApp(staticdir=None)
        for h in a.handlers[0][1]:
            if h.regex.match(path):
                klass = h.handler_class
        r = httpserver.HTTPRequest("GET", path)
        del r.connection
        k = klass(a, r)
        k._transforms = []
        return k

    def test_index(self):
        page = self.dummy_page("/")
        page.get()
        assert "".join(page._write_buffer)

    def test_help(self):
        page = self.dummy_page("/help")
        page.get()
        assert "".join(page._write_buffer)



tests = [
    uApplication(),
]
