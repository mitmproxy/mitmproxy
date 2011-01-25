from libmproxy import console, proxy, utils, filt, flow
import libpry

def treq(conn=None):
    if not conn:
        conn = proxy.BrowserConnection("address", 22)
    headers = utils.Headers()
    headers["header"] = ["qvalue"]
    return proxy.Request(conn, "host", 80, "http", "GET", "/path", headers, "content")


def tresp(req=None):
    if not req:
        req = treq()
    headers = utils.Headers()
    headers["header_response"] = ["svalue"]
    return proxy.Response(req, 200, "HTTP/1.1", "message", headers, "content_response")


def tflow():
    bc = proxy.BrowserConnection("address", 22)
    return console.ConsoleFlow(bc)


class uState(libpry.AutoTree):
    def test_backup(self):
        bc = proxy.BrowserConnection("address", 22)
        c = console.ConsoleState()
        f = console.ConsoleFlow(bc)
        c.add_browserconnect(f)

        f.backup()
        c.revert(f)

    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        bc = proxy.BrowserConnection("address", 22)
        c = console.ConsoleState()
        f = console.ConsoleFlow(bc)
        c.add_browserconnect(f)
        assert c.lookup(bc)
        assert c.get_focus() == (f, 0)

        req = treq(bc)
        assert c.add_request(req)
        assert len(c.flow_list) == 1
        assert c.lookup(req)

        newreq = treq()
        assert not c.add_request(newreq)
        assert not c.lookup(newreq)

        resp = tresp(req)
        assert c.add_response(resp)
        assert len(c.flow_list) == 1
        assert f.waiting == False
        assert c.lookup(resp)

        newresp = tresp()
        assert not c.add_response(newresp)
        assert not c.lookup(newresp)

    def test_err(self):
        bc = proxy.BrowserConnection("address", 22)
        c = console.ConsoleState()
        f = console.ConsoleFlow(bc)
        c.add_browserconnect(f)
        e = proxy.Error(bc, "message")
        assert c.add_error(e)

        e = proxy.Error(proxy.BrowserConnection("address", 22), "message")
        assert not c.add_error(e)

    def test_view(self):
        c = console.ConsoleState()

        f = tflow()
        c.add_browserconnect(f)
        assert len(c.view) == 1
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 0
        c.set_limit(None)

        
        f = tflow()
        req = treq(f.connection)
        c.add_browserconnect(f)
        c.add_request(req)
        assert len(c.view) == 2
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 1
        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 0

    def test_focus(self):
        """
            normal flow:

                connect -> request -> response
        """
        c = console.ConsoleState()

        bc = proxy.BrowserConnection("address", 22)
        f = console.ConsoleFlow(bc)
        c.add_browserconnect(f)
        assert c.get_focus() == (f, 0)
        assert c.get_from_pos(0) == (f, 0)
        assert c.get_from_pos(1) == (None, None)
        assert c.get_next(0) == (None, None)

        bc2 = proxy.BrowserConnection("address", 22)
        f2 = console.ConsoleFlow(bc2)
        c.add_browserconnect(f2)
        assert c.get_focus() == (f, 1)
        assert c.get_next(0) == (f, 1)
        assert c.get_prev(1) == (f2, 0)
        assert c.get_next(1) == (None, None)

        c.set_focus(0)
        assert c.get_focus() == (f2, 0)
        c.set_focus(-1)
        assert c.get_focus() == (f2, 0)

        c.delete_flow(f2)
        assert c.get_focus() == (f, 0)
        c.delete_flow(f)
        assert c.get_focus() == (None, None)

    def _add_request(self, state):
        f = tflow()
        state.add_browserconnect(f)
        q = treq(f.connection)
        state.add_request(q)
        return f

    def _add_response(self, state):
        f = self._add_request(state)
        r = tresp(f.request)
        state.add_response(r)

    def test_focus_view(self):
        c = console.ConsoleState()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 3
        assert c.focus == 2

    def test_delete_last(self):
        c = console.ConsoleState()
        f1 = tflow()
        f2 = tflow()
        c.add_browserconnect(f1)
        c.add_browserconnect(f2)
        c.set_focus(1)
        c.delete_flow(f1)
        assert c.focus == 0

    def test_kill_flow(self):
        c = console.ConsoleState()
        f = tflow()
        c.add_browserconnect(f)
        c.kill_flow(f)
        assert not c.flow_list

    def test_clear(self):
        c = console.ConsoleState()
        f = tflow()
        c.add_browserconnect(f)
        f.intercepting = True

        c.clear()
        assert len(c.flow_list) == 1
        f.intercepting = False
        c.clear()
        assert len(c.flow_list) == 0


class uFlow(libpry.AutoTree):
    def test_match(self):
        f = tflow()
        f.response = tresp()
        f.request = f.response.request
        assert not f.match(filt.parse("~b test"))

    def test_backup(self):
        f = tflow()
        f.backup()
        f.revert()

    def test_simple(self):
        f = tflow()
        assert f.get_text()

        f.request = treq()
        assert f.get_text()

        f.response = tresp()
        f.response.headers["content-type"] = ["text/html"]
        assert f.get_text()
        f.response.code = 404
        assert f.get_text()

        f.focus = True
        assert f.get_text()

        f.connection = flow.ReplayConnection()
        assert f.get_text()

        f.response = None
        assert f.get_text()

        f.error = proxy.Error(200, "test")
        assert f.get_text()

    def test_kill(self):
        f = tflow()
        f.request = treq()
        f.intercept()
        assert not f.request.acked
        f.kill()
        assert f.request.acked
        f.intercept()
        f.response = tresp()
        f.request = f.response.request
        f.request.ack()
        assert not f.response.acked
        f.kill()
        assert f.response.acked

    def test_accept_intercept(self):
        f = tflow()
        f.request = treq()
        f.intercept()
        assert not f.request.acked
        f.accept_intercept()
        assert f.request.acked
        f.response = tresp()
        f.request = f.response.request
        f.intercept()
        f.request.ack()
        assert not f.response.acked
        f.accept_intercept()
        assert f.response.acked

    def test_serialization(self):
        f = console.ConsoleFlow(None)
        f.request = treq()



class uformat_keyvals(libpry.AutoTree):
    def test_simple(self):
        assert console.format_keyvals(
            [
                ("aa", "bb"),
                ("cc", "dd"),
            ]
        )


tests = [
    uFlow(),
    uformat_keyvals(),
    uState()
]
