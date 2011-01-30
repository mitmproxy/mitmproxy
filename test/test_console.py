from libmproxy import console, proxy, filt, flow
import utils
import libpry


class uState(libpry.AutoTree):
    def test_backup(self):
        bc = proxy.BrowserConnection("address", 22)
        c = console.ConsoleState()
        f = flow.Flow(bc)
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
        f = flow.Flow(bc)
        c.add_browserconnect(f)
        assert c.lookup(bc)
        assert c.get_focus() == (f, 0)

        req = utils.treq(bc)
        assert c.add_request(req)
        assert len(c.flow_list) == 1
        assert c.lookup(req)

        newreq = utils.treq()
        assert not c.add_request(newreq)
        assert not c.lookup(newreq)

        resp = utils.tresp(req)
        assert c.add_response(resp)
        assert len(c.flow_list) == 1
        assert c.lookup(resp)

        newresp = utils.tresp()
        assert not c.add_response(newresp)
        assert not c.lookup(newresp)

    def test_err(self):
        bc = proxy.BrowserConnection("address", 22)
        c = console.ConsoleState()
        f = flow.Flow(bc)
        c.add_browserconnect(f)
        e = proxy.Error(bc, "message")
        assert c.add_error(e)

        e = proxy.Error(proxy.BrowserConnection("address", 22), "message")
        assert not c.add_error(e)

    def test_view(self):
        c = console.ConsoleState()

        f = utils.tflow()
        c.add_browserconnect(f)
        assert len(c.view) == 1
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 0
        c.set_limit(None)

        
        f = utils.tflow()
        req = utils.treq(f.connection)
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
        f = flow.Flow(bc)
        c.add_browserconnect(f)
        assert c.get_focus() == (f, 0)
        assert c.get_from_pos(0) == (f, 0)
        assert c.get_from_pos(1) == (None, None)
        assert c.get_next(0) == (None, None)

        bc2 = proxy.BrowserConnection("address", 22)
        f2 = flow.Flow(bc2)
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
        f = utils.tflow()
        state.add_browserconnect(f)
        q = utils.treq(f.connection)
        state.add_request(q)
        return f

    def _add_response(self, state):
        f = self._add_request(state)
        r = utils.tresp(f.request)
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
        f1 = utils.tflow()
        f2 = utils.tflow()
        c.add_browserconnect(f1)
        c.add_browserconnect(f2)
        c.set_focus(1)
        c.delete_flow(f1)
        assert c.focus == 0

    def test_kill_flow(self):
        c = console.ConsoleState()
        f = utils.tflow()
        c.add_browserconnect(f)
        c.kill_flow(f)
        assert not c.flow_list

    def test_clear(self):
        c = console.ConsoleState()
        f = utils.tflow()
        c.add_browserconnect(f)
        f.intercepting = True

        c.clear()
        assert len(c.flow_list) == 1
        f.intercepting = False
        c.clear()
        assert len(c.flow_list) == 0

    def test_dump_flows(self):
        c = console.ConsoleState()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)

        dump = c.dump_flows()
        c.clear()
        c.load_flows(dump)
        assert isinstance(c.flow_list[0], flow.Flow)


class uformat_keyvals(libpry.AutoTree):
    def test_simple(self):
        assert console.format_keyvals(
            [
                ("aa", "bb"),
                ("cc", "dd"),
            ]
        )

class uPathCompleter(libpry.AutoTree):
    def test_completion(self):
        c = console._PathCompleter(True)
        c.reset()
        c.lookup = [
            ("a", "x/a"),
            ("aa", "x/aa"),
        ]
        assert c.complete("a") == "a"
        assert c.final == "x/a"
        assert c.complete("a") == "aa"
        assert c.complete("a") == "a"

        c = console._PathCompleter(True)
        r = c.complete("l")
        assert c.final.endswith(r)

        c.reset()
        assert c.complete("/nonexistent") == "/nonexistent"
        assert c.final == "/nonexistent"
        c.reset()
        assert c.complete("~") != "~"

        c.reset()
        s = "thisisatotallynonexistantpathforsure"
        assert c.complete(s) == s
        assert c.final == s



tests = [
    uformat_keyvals(),
    uState(), 
    uPathCompleter()
]
